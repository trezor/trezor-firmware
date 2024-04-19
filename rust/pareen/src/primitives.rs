use core::marker::PhantomData;
use core::ops::Mul;

use crate::{Anim, Fun};

use num_traits::{FloatConst, float::FloatCore};

/// Turn any function `Fn(T) -> V` into an [`Anim`](struct.Anim.html).
///
/// # Example
/// ```
/// # use assert_approx_eq::assert_approx_eq;
/// fn my_crazy_function(t: f32) -> f32 {
///     42.0 / t
/// }
///
/// let anim = pareen::fun(my_crazy_function);
///
/// assert_approx_eq!(anim.eval(1.0), 42.0);
/// assert_approx_eq!(anim.eval(2.0), 21.0);
/// ```
pub fn fun<T, V>(f: impl Fn(T) -> V) -> Anim<impl Fun<T = T, V = V>> {
    From::from(f)
}

struct WrapFn<T, V, F: Fn(T) -> V>(F, PhantomData<(T, V)>);

impl<T, V, F> From<F> for Anim<WrapFn<T, V, F>>
where
    F: Fn(T) -> V,
{
    fn from(f: F) -> Self {
        Anim(WrapFn(f, PhantomData))
    }
}

impl<T, V, F> Fun for WrapFn<T, V, F>
where
    F: Fn(T) -> V,
{
    type T = T;
    type V = V;

    fn eval(&self, t: T) -> V {
        self.0(t)
    }
}

/// A constant animation, always returning the same value.
///
/// # Example
/// ```
/// # use assert_approx_eq::assert_approx_eq;
/// let anim = pareen::constant(1.0f32);
///
/// assert_approx_eq!(anim.eval(-10000.0f32), 1.0);
/// assert_approx_eq!(anim.eval(0.0), 1.0);
/// assert_approx_eq!(anim.eval(42.0), 1.0);
/// ```
pub fn constant<T, V: Clone>(c: V) -> Anim<impl Fun<T = T, V = V>> {
    fun(move |_| c.clone())
}

#[doc(hidden)]
#[derive(Debug, Clone)]
pub struct ConstantClosure<T, V>(V, PhantomData<T>);

impl<T, V> Fun for ConstantClosure<T, V>
where
    V: Clone,
{
    type T = T;
    type V = V;

    fn eval(&self, _: T) -> V {
        self.0.clone()
    }
}

impl<T, V> From<V> for ConstantClosure<T, V>
where
    V: Clone,
{
    fn from(v: V) -> Self {
        ConstantClosure(v, PhantomData)
    }
}

impl<T, V> From<V> for Anim<ConstantClosure<T, V>>
where
    V: Clone,
{
    fn from(v: V) -> Self {
        Anim(ConstantClosure::from(v))
    }
}

/// An animation that returns a value proportional to time.
///
/// # Example
///
/// Scale time with a factor of three:
/// ```
/// # use assert_approx_eq::assert_approx_eq;
/// let anim = pareen::prop(3.0f32);
///
/// assert_approx_eq!(anim.eval(0.0f32), 0.0);
/// assert_approx_eq!(anim.eval(3.0), 9.0);
/// ```
pub fn prop<T, V, W>(m: V) -> Anim<impl Fun<T = T, V = W>>
where
    V: Clone + Mul<Output = W> + From<T>,
{
    fun(move |t| m.clone() * From::from(t))
}

/// An animation that returns time as its value.
///
/// This is the same as [`prop`](fn.prop.html) with a factor of one.
///
/// # Examples
/// ```
/// let anim = pareen::id::<isize, isize>();
///
/// assert_eq!(anim.eval(-100), -100);
/// assert_eq!(anim.eval(0), 0);
/// assert_eq!(anim.eval(100), 100);
/// ```
/// ```
/// # use assert_approx_eq::assert_approx_eq;
/// let anim = pareen::id::<f32, f32>() * 3.0 + 4.0;
///
/// assert_approx_eq!(anim.eval(0.0), 4.0);
/// assert_approx_eq!(anim.eval(100.0), 304.0);
/// ```
pub fn id<T, V>() -> Anim<impl Fun<T = T, V = V>>
where
    V: From<T>,
{
    fun(From::from)
}

/// Proportionally increase value from zero to 2π.
pub fn circle<T, V>() -> Anim<impl Fun<T = T, V = V>>
where
    T: FloatCore,
    V: FloatCore + FloatConst + From<T>,
{
    prop(V::PI() * (V::one() + V::one()))
}

/// Proportionally increase value from zero to π.
pub fn half_circle<T, V>() -> Anim<impl Fun<T = T, V = V>>
where
    T: FloatCore,
    V: FloatCore + FloatConst + From<T>,
{
    prop(V::PI())
}

/// Proportionally increase value from zero to π/2.
pub fn quarter_circle<T, V>() -> Anim<impl Fun<T = T, V = V>>
where
    T: FloatCore,
    V: FloatCore + FloatConst + From<T>,
{
    prop(V::PI() * (V::one() / (V::one() + V::one())))
}

/// Evaluate a quadratic polynomial in time.
pub fn quadratic<T>(w: &[T; 3]) -> Anim<impl Fun<T = T, V = T> + '_>
where
    T: FloatCore,
{
    fun(move |t| {
        let t2 = t * t;

        w[0] * t2 + w[1] * t + w[2]
    })
}

/// Evaluate a cubic polynomial in time.
pub fn cubic<T>(w: &[T; 4]) -> Anim<impl Fun<T = T, V = T> + '_>
where
    T: FloatCore,
{
    fun(move |t| {
        let t2 = t * t;
        let t3 = t2 * t;

        w[0] * t3 + w[1] * t2 + w[2] * t + w[3]
    })
}

/// Count from 0 to `end` (non-inclusive) cyclically, at the given frames per
/// second rate.
///
/// # Example
/// ```
/// let anim = pareen::cycle(3, 5.0);
/// assert_eq!(anim.eval(0.0), 0);
/// assert_eq!(anim.eval(0.1), 0);
/// assert_eq!(anim.eval(0.3), 1);
/// assert_eq!(anim.eval(0.5), 2);
/// assert_eq!(anim.eval(0.65), 0);
///
/// assert_eq!(anim.eval(-0.1), 2);
/// assert_eq!(anim.eval(-0.3), 1);
/// assert_eq!(anim.eval(-0.5), 0);
/// ```
pub fn cycle(end: usize, fps: f32) -> Anim<impl Fun<T = f32, V = usize>> {
    fun(move |t: f32| {
        if t < 0.0 {
            let tau = (t.abs() * fps) as usize;

            end - 1 - tau % end
        } else {
            let tau = (t * fps) as usize;

            tau % end
        }
    })
}

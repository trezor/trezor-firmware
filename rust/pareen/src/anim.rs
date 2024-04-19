use core::ops::{Add, Mul, RangeInclusive, Sub};

#[cfg(any(feature = "std", feature = "libm"))]
use num_traits::Float;
use num_traits::{float::FloatCore, Num, One, Zero};

use crate::{constant, fun, id};

/// A `Fun` represents anything that maps from some type `T` to another
/// type `V`.
///
/// `T` usually stands for time and `V` for some value that is parameterized by
/// time.
///
/// ## Implementation details
/// The only reason that we define this trait instead of just using `Fn(T) -> V`
/// is so that the library works in stable rust. Having this type allows us to
/// implement e.g. `std::ops::Add` for [`Anim<F>`](struct.Anim.html) where
/// `F: Fun`. Without this trait, it becomes difficult (impossible?) to provide
/// a name for `Add::Output`, unless you have the unstable feature
/// `type_alias_impl_trait` or `fn_traits`.
///
/// In contrast to `std::ops::FnOnce`, both input _and_ output are associated
/// types of `Fun`. The main reason is that this makes types smaller for the
/// user of the library. I have not observed any downsides to this yet.
pub trait Fun {
    /// The function's input type. Usually time.
    type T;

    /// The function's output type.
    type V;

    /// Evaluate the function at time `t`.
    fn eval(&self, t: Self::T) -> Self::V;
}

impl<'a, F> Fun for &'a F
where
    F: Fun,
{
    type T = F::T;
    type V = F::V;

    fn eval(&self, t: Self::T) -> Self::V {
        (*self).eval(t)
    }
}

/// `Anim` is the main type provided by pareen. It is a wrapper around any type
/// implementing [`Fun`](trait.Fun.html).
///
/// `Anim` provides methods that transform or compose animations, allowing
/// complex animations to be created out of simple pieces.
#[derive(Clone, Debug)]
pub struct Anim<F>(pub F);

impl<F> Anim<F>
where
    F: Fun,
{
    /// Evaluate the animation at time `t`.
    pub fn eval(&self, t: F::T) -> F::V {
        self.0.eval(t)
    }

    /// Transform an animation so that it applies a given function to its
    /// values.
    ///
    /// # Example
    ///
    /// Turn `(2.0 * t)` into `(2.0 * t).sqrt() + 2.0 * t`:
    /// ```
    /// # use assert_approx_eq::assert_approx_eq;
    /// let anim = pareen::prop(2.0f32).map(|value| value.sqrt() + value);
    ///
    /// assert_approx_eq!(anim.eval(1.0), 2.0f32.sqrt() + 2.0);
    /// ```
    pub fn map<W>(self, f: impl Fn(F::V) -> W) -> Anim<impl Fun<T = F::T, V = W>> {
        self.map_anim(fun(f))
    }

    /// Transform an animation so that it modifies time according to the given
    /// function before evaluating the animation.
    ///
    /// # Example
    /// Run an animation two times slower:
    /// ```
    /// let anim = pareen::cubic(&[1.0, 1.0, 1.0, 1.0]);
    /// let slower_anim = anim.map_time(|t: f32| t / 2.0);
    /// ```
    pub fn map_time<S>(self, f: impl Fn(S) -> F::T) -> Anim<impl Fun<T = S, V = F::V>> {
        fun(f).map_anim(self)
    }

    /// Converts from `Anim<F>` to `Anim<&F>`.
    pub fn as_ref(&self) -> Anim<&F> {
        Anim(&self.0)
    }

    pub fn map_anim<W, G, A>(self, anim: A) -> Anim<impl Fun<T = F::T, V = W>>
    where
        G: Fun<T = F::V, V = W>,
        A: Into<Anim<G>>,
    {
        // Nested closures result in exponential compilation time increase, and we
        // expect map_anim to be used often. Thus, we avoid using `pareen::fun` here.
        // For reference: https://github.com/rust-lang/rust/issues/72408
        Anim(MapClosure(self.0, anim.into().0))
    }

    pub fn map_time_anim<S, G, A>(self, anim: A) -> Anim<impl Fun<T = S, V = F::V>>
    where
        G: Fun<T = S, V = F::T>,
        A: Into<Anim<G>>,
    {
        anim.into().map_anim(self)
    }

    pub fn into_fn(self) -> impl Fn(F::T) -> F::V {
        move |t| self.eval(t)
    }
}

impl<F> Anim<F>
where
    F: Fun,
    F::T: Clone + Mul<Output = F::T>,
{
    pub fn scale_time(self, t_scale: F::T) -> Anim<impl Fun<T = F::T, V = F::V>> {
        self.map_time(move |t| t * t_scale.clone())
    }
}

impl<F> Fun for Option<F>
where
    F: Fun,
{
    type T = F::T;
    type V = Option<F::V>;

    fn eval(&self, t: F::T) -> Option<F::V> {
        self.as_ref().map(|f| f.eval(t))
    }
}

#[doc(hidden)]
#[derive(Debug, Clone)]
pub struct MapClosure<F, G>(F, G);

impl<F, G> Fun for MapClosure<F, G>
where
    F: Fun,
    G: Fun<T = F::V>,
{
    type T = F::T;
    type V = G::V;

    fn eval(&self, t: F::T) -> G::V {
        self.1.eval(self.0.eval(t))
    }
}

impl<T, X, Y, F> Anim<F>
where
    F: Fun<T = T, V = (X, Y)>,
{
    pub fn fst(self) -> Anim<impl Fun<T = F::T, V = X>> {
        self.map(|(x, _)| x)
    }

    pub fn snd(self) -> Anim<impl Fun<T = F::T, V = Y>> {
        self.map(|(_, y)| y)
    }
}

impl<F> Anim<F>
where
    F: Fun,
    F::T: Clone,
{
    /// Combine two animations into one, yielding an animation having pairs as
    /// the values.
    pub fn zip<G, A>(self, other: A) -> Anim<impl Fun<T = F::T, V = (F::V, G::V)>>
    where
        G: Fun<T = F::T>,
        A: Into<Anim<G>>,
    {
        // Nested closures result in exponential compilation time increase, and we
        // expect zip to be used frequently. Thus, we avoid using `pareen::fun` here.
        // For reference: https://github.com/rust-lang/rust/issues/72408
        Anim(ZipClosure(self.0, other.into().0))
    }

    pub fn bind<W, G>(self, f: impl Fn(F::V) -> Anim<G>) -> Anim<impl Fun<T = F::T, V = W>>
    where
        G: Fun<T = F::T, V = W>,
    {
        fun(move |t: F::T| f(self.eval(t.clone())).eval(t))
    }
}

impl<'a, T, V, F> Anim<F>
where
    V: 'a + Copy,
    F: Fun<T = T, V = &'a V> + 'a,
{
    pub fn copied(self) -> Anim<impl Fun<T = T, V = V> + 'a> {
        self.map(|x| *x)
    }
}

impl<'a, T, V, F> Anim<F>
where
    V: 'a + Clone,
    F: Fun<T = T, V = &'a V> + 'a,
{
    pub fn cloned(self) -> Anim<impl Fun<T = T, V = V> + 'a> {
        self.map(|x| x.clone())
    }
}

#[doc(hidden)]
#[derive(Debug, Clone)]
pub struct ZipClosure<F, G>(F, G);

impl<F, G> Fun for ZipClosure<F, G>
where
    F: Fun,
    F::T: Clone,
    G: Fun<T = F::T>,
{
    type T = F::T;
    type V = (F::V, G::V);

    fn eval(&self, t: F::T) -> Self::V {
        (self.0.eval(t.clone()), self.1.eval(t))
    }
}

impl<F> Anim<F>
where
    F: Fun,
    F::T: Copy + Sub<Output = F::T>,
{
    /// Shift an animation in time, so that it is moved to the right by `t_delay`.
    pub fn shift_time(self, t_delay: F::T) -> Anim<impl Fun<T = F::T, V = F::V>> {
        (id::<F::T, F::T>() - t_delay).map_anim(self)
    }
}

impl<F> Anim<F>
where
    F: Fun,
    F::T: Clone + PartialOrd,
{
    /// Concatenate `self` with another animation in time, using `self` until
    /// time `self_end` (non-inclusive), and then switching to `next`.
    ///
    /// # Examples
    /// Switch from one constant value to another:
    /// ```
    /// # use assert_approx_eq::assert_approx_eq;
    /// let anim = pareen::constant(1.0f32).switch(0.5f32, 2.0);
    ///
    /// assert_approx_eq!(anim.eval(0.0), 1.0);
    /// assert_approx_eq!(anim.eval(0.5), 2.0);
    /// assert_approx_eq!(anim.eval(42.0), 2.0);
    /// ```
    ///
    /// Piecewise combinations of functions:
    /// ```
    /// let cubic_1 = pareen::cubic(&[4.4034, 0.0, -4.5455e-2, 0.0]);
    /// let cubic_2 = pareen::cubic(&[-1.2642e1, 2.0455e1, -8.1364, 1.0909]);
    /// let cubic_3 = pareen::cubic(&[1.6477e1, -4.9432e1, 4.7773e1, -1.3818e1]);
    ///
    /// // Use cubic_1 for [0.0, 0.4), cubic_2 for [0.4, 0.8) and
    /// // cubic_3 for [0.8, ..).
    /// let anim = cubic_1.switch(0.4, cubic_2).switch(0.8, cubic_3);
    /// ```
    pub fn switch<G, A>(self, self_end: F::T, next: A) -> Anim<impl Fun<T = F::T, V = F::V>>
    where
        G: Fun<T = F::T, V = F::V>,
        A: Into<Anim<G>>,
    {
        // Nested closures result in exponential compilation time increase, and we
        // expect switch to be used frequently. Thus, we avoid using `pareen::fun` here.
        // For reference: https://github.com/rust-lang/rust/issues/72408
        cond(switch_cond(self_end), self, next)
    }

    /// Play `self` in time range `range`, and `surround` outside of the time range.
    ///
    /// # Examples
    /// ```
    /// # use assert_approx_eq::assert_approx_eq;
    /// let anim = pareen::constant(10.0f32).surround(2.0..=5.0, 20.0);
    ///
    /// assert_approx_eq!(anim.eval(0.0), 20.0);
    /// assert_approx_eq!(anim.eval(2.0), 10.0);
    /// assert_approx_eq!(anim.eval(4.0), 10.0);
    /// assert_approx_eq!(anim.eval(5.0), 10.0);
    /// assert_approx_eq!(anim.eval(6.0), 20.0);
    /// ```
    pub fn surround<G, A>(
        self,
        range: RangeInclusive<F::T>,
        surround: A,
    ) -> Anim<impl Fun<T = F::T, V = F::V>>
    where
        G: Fun<T = F::T, V = F::V>,
        A: Into<Anim<G>>,
    {
        // Nested closures result in exponential compilation time increase, and we
        // expect surround to be used frequently. Thus, we avoid using `pareen::fun` here.
        // For reference: https://github.com/rust-lang/rust/issues/72408
        cond(surround_cond(range), self, surround)
    }
}

fn switch_cond<T: PartialOrd>(self_end: T) -> Anim<impl Fun<T = T, V = bool>> {
    fun(move |t| t < self_end)
}

fn surround_cond<T: PartialOrd>(range: RangeInclusive<T>) -> Anim<impl Fun<T = T, V = bool>> {
    fun(move |t| range.contains(&t))
}

impl<F> Anim<F>
where
    F: Fun,
    F::T: Clone + PartialOrd,
    F::V: Clone,
{
    /// Play `self` until time `self_end`, then always return the value of
    /// `self` at time `self_end`.
    pub fn hold(self, self_end: F::T) -> Anim<impl Fun<T = F::T, V = F::V>> {
        let end_value = self.eval(self_end.clone());

        self.switch(self_end, constant(end_value))
    }
}

impl<F> Anim<F>
where
    F: Fun,
    F::T: Copy + PartialOrd + Sub<Output = F::T>,
{
    /// Play two animations in sequence, first playing `self` until time
    /// `self_end` (non-inclusive), and then switching to `next`. Note that
    /// `next` will see time starting at zero once it plays.
    ///
    /// # Example
    /// Stay at value `5.0` for ten seconds, then increase value proportionally:
    /// ```
    /// # use assert_approx_eq::assert_approx_eq;
    /// let anim_1 = pareen::constant(5.0f32);
    /// let anim_2 = pareen::prop(2.0f32) + 5.0;
    /// let anim = anim_1.seq(10.0, anim_2);
    ///
    /// assert_approx_eq!(anim.eval(0.0), 5.0);
    /// assert_approx_eq!(anim.eval(10.0), 5.0);
    /// assert_approx_eq!(anim.eval(11.0), 7.0);
    /// ```
    pub fn seq<G, A>(self, self_end: F::T, next: A) -> Anim<impl Fun<T = F::T, V = F::V>>
    where
        G: Fun<T = F::T, V = F::V>,
        A: Into<Anim<G>>,
    {
        self.switch(self_end.clone(), next.into().shift_time(self_end))
    }

    pub fn seq_continue<G, A, H>(
        self,
        self_end: F::T,
        next_fn: H,
    ) -> Anim<impl Fun<T = F::T, V = F::V>>
    where
        G: Fun<T = F::T, V = F::V>,
        A: Into<Anim<G>>,
        H: Fn(F::V) -> A,
    {
        let next = next_fn(self.eval(self_end.clone())).into();

        self.seq(self_end, next)
    }
}

impl<F> Anim<F>
where
    F: Fun,
    F::T: Clone + Sub<Output = F::T>,
{
    /// Play an animation backwards, starting at time `end`.
    ///
    /// # Example
    ///
    /// ```
    /// # use assert_approx_eq::assert_approx_eq;
    /// let anim = pareen::prop(2.0f32).backwards(1.0);
    ///
    /// assert_approx_eq!(anim.eval(0.0f32), 2.0);
    /// assert_approx_eq!(anim.eval(1.0f32), 0.0);
    /// ```
    pub fn backwards(self, end: F::T) -> Anim<impl Fun<T = F::T, V = F::V>> {
        (constant(end) - id()).map_anim(self)
    }
}

impl<F> Anim<F>
where
    F: Fun,
    F::T: Copy,
    F::V: Copy + Num,
{
    /// Given animation values in `[0.0 .. 1.0]`, this function transforms the
    /// values so that they are in `[min .. max]`.
    ///
    /// # Example
    /// ```
    /// # use assert_approx_eq::assert_approx_eq;
    /// let min = -3.0f32;
    /// let max = 10.0;
    /// let anim = pareen::id().scale_min_max(min, max);
    ///
    /// assert_approx_eq!(anim.eval(0.0f32), min);
    /// assert_approx_eq!(anim.eval(1.0f32), max);
    /// ```
    pub fn scale_min_max(self, min: F::V, max: F::V) -> Anim<impl Fun<T = F::T, V = F::V>> {
        self * (max.clone() - min) + min
    }
}

#[cfg(any(feature = "std", feature = "libm"))]
impl<F> Anim<F>
where
    F: Fun,
    F::V: Float,
{
    /// Apply `Float::sin` to the animation values.
    pub fn sin(self) -> Anim<impl Fun<T = F::T, V = F::V>> {
        self.map(Float::sin)
    }

    /// Apply `Float::cos` to the animation values.
    pub fn cos(self) -> Anim<impl Fun<T = F::T, V = F::V>> {
        self.map(Float::cos)
    }

    /// Apply `Float::powf` to the animation values.
    pub fn powf(self, e: F::V) -> Anim<impl Fun<T = F::T, V = F::V>> {
        self.map(move |v| v.powf(e))
    }
}

impl<F> Anim<F>
where
    F: Fun,
    F::V: FloatCore,
{
    /// Apply `FloatCore::abs` to the animation values.
    pub fn abs(self) -> Anim<impl Fun<T = F::T, V = F::V>> {
        self.map(FloatCore::abs)
    }

    /// Apply `FloatCore::powi` to the animation values.
    pub fn powi(self, n: i32) -> Anim<impl Fun<T = F::T, V = F::V>> {
        self.map(move |v| v.powi(n))
    }
}

impl<F> Anim<F>
where
    F: Fun,
    F::T: Copy + FloatCore,
{
    /// Transform an animation in time, so that its time `[0 .. 1]` is shifted
    /// and scaled into the given `range`.
    ///
    /// In other words, this function can both delay and speed up or slow down a
    /// given animation.
    ///
    /// # Example
    ///
    /// Go from zero to 2π in half a second:
    /// ```
    /// # use assert_approx_eq::assert_approx_eq;
    /// // From zero to 2π in one second
    /// let angle = pareen::circle::<f32, f32>();
    ///
    /// // From zero to 2π in time range [0.5 .. 1.0]
    /// let anim = angle.squeeze(0.5..=1.0);
    ///
    /// assert_approx_eq!(anim.eval(0.5), 0.0);
    /// assert_approx_eq!(anim.eval(1.0), std::f32::consts::PI * 2.0);
    /// ```
    pub fn squeeze(self, range: RangeInclusive<F::T>) -> Anim<impl Fun<T = F::T, V = F::V>> {
        let time_shift = *range.start();
        let time_scale = F::T::one() / (*range.end() - *range.start());

        self.map_time(move |t| (t - time_shift) * time_scale)
    }

    /// Transform an animation in time, so that its time `[0 .. 1]` is shifted
    /// and scaled into the given `range`.
    ///
    /// In other words, this function can both delay and speed up or slow down a
    /// given animation.
    ///
    /// For time outside of the given `range`, the `surround` animation is used
    /// instead.
    ///
    /// # Example
    ///
    /// Go from zero to 2π in half a second:
    /// ```
    /// # use assert_approx_eq::assert_approx_eq;
    /// // From zero to 2π in one second
    /// let angle = pareen::circle();
    ///
    /// // From zero to 2π in time range [0.5 .. 1.0]
    /// let anim = angle.squeeze_and_surround(0.5..=1.0, 42.0);
    ///
    /// assert_approx_eq!(anim.eval(0.0f32), 42.0f32);
    /// assert_approx_eq!(anim.eval(0.5), 0.0);
    /// assert_approx_eq!(anim.eval(1.0), std::f32::consts::PI * 2.0);
    /// assert_approx_eq!(anim.eval(1.1), 42.0);
    /// ```
    pub fn squeeze_and_surround<G, A>(
        self,
        range: RangeInclusive<F::T>,
        surround: A,
    ) -> Anim<impl Fun<T = F::T, V = F::V>>
    where
        G: Fun<T = F::T, V = F::V>,
        A: Into<Anim<G>>,
    {
        self.squeeze(range.clone()).surround(range, surround)
    }

    /// Play two animations in sequence, first playing `self` until time
    /// `self_end` (non-inclusive), and then switching to `next`. The animations
    /// are squeezed in time so that they fit into `[0 .. 1]` together.
    ///
    /// `self` is played in time `[0 .. self_end)`, and then `next` is played
    /// in time [self_end .. 1]`.
    pub fn seq_squeeze<G, A>(self, self_end: F::T, next: A) -> Anim<impl Fun<T = F::T, V = F::V>>
    where
        G: Fun<T = F::T, V = F::V>,
        A: Into<Anim<G>>,
    {
        let first = self.squeeze(Zero::zero()..=self_end);
        let second = next.into().squeeze(self_end..=One::one());

        first.switch(self_end, second)
    }

    /// Repeat an animation forever.
    pub fn repeat(self, period: F::T) -> Anim<impl Fun<T = F::T, V = F::V>> {
        self.map_time(move |t: F::T| (t * period.recip()).fract() * period)
    }
}

impl<W, F> Anim<F>
where
    F: Fun,
    F::T: Copy + Mul<W, Output = W>,
    F::V: Copy + Add<W, Output = F::V> + Sub<Output = W>,
{
    /// Linearly interpolate between two animations, starting at time zero and
    /// finishing at time one.
    ///
    /// # Examples
    ///
    /// Linearly interpolate between two constant values:
    /// ```
    /// # use assert_approx_eq::assert_approx_eq;
    /// let anim = pareen::constant(5.0f32).lerp(10.0);
    ///
    /// assert_approx_eq!(anim.eval(0.0f32), 5.0);
    /// assert_approx_eq!(anim.eval(0.5), 7.5);
    /// assert_approx_eq!(anim.eval(1.0), 10.0);
    /// assert_approx_eq!(anim.eval(2.0), 15.0);
    /// ```
    #[cfg_attr(any(feature = "std", feature = "libm"), doc = r##"
It is also possible to linearly interpolate between two non-constant
animations:
```
let anim = pareen::circle().sin().lerp(pareen::circle().cos());
let value: f32 = anim.eval(0.5f32);
```
    "##)]
    pub fn lerp<G, A>(self, other: A) -> Anim<impl Fun<T = F::T, V = F::V>>
    where
        G: Fun<T = F::T, V = F::V>,
        A: Into<Anim<G>>,
    {
        let other = other.into();

        fun(move |t| {
            let a = self.eval(t);
            let b = other.eval(t);

            let delta = b - a;

            a + t * delta
        })
    }
}

impl<V, F> Anim<F>
where
    F: Fun<V = Option<V>>,
    F::T: Clone,
{
    /// Unwrap an animation of optional values.
    ///
    /// At any time, returns the animation value if it is not `None`, or the
    /// given `default` value otherwise.
    ///
    /// # Examples
    ///
    /// ```
    /// let anim1 = pareen::constant(Some(42)).unwrap_or(-1);
    /// assert_eq!(anim1.eval(2), 42);
    /// assert_eq!(anim1.eval(3), 42);
    /// ```
    ///
    /// ```
    /// let cond = pareen::fun(|t| t % 2 == 0);
    /// let anim1 = pareen::cond(cond, Some(42), None).unwrap_or(-1);
    /// assert_eq!(anim1.eval(2), 42);
    /// assert_eq!(anim1.eval(3), -1);
    /// ```
    pub fn unwrap_or<G, A>(self, default: A) -> Anim<impl Fun<T = F::T, V = V>>
    where
        G: Fun<T = F::T, V = V>,
        A: Into<Anim<G>>,
    {
        self.zip(default.into())
            .map(|(v, default)| v.unwrap_or(default))
    }

    /// Applies a function to the contained value (if any), or returns the
    /// provided default (if not).
    ///
    /// Note that the function `f` itself returns an animation.
    ///
    /// # Example
    ///
    /// Animate a player's position offset if it is moving:
    /// ```
    /// # use assert_approx_eq::assert_approx_eq;
    /// fn my_offset_anim(
    ///     move_dir: Option<f32>,
    /// ) -> pareen::Anim<impl pareen::Fun<T = f32, V = f32>> {
    ///     let move_speed = 2.0f32;
    ///
    ///     pareen::constant(move_dir).map_or(
    ///         0.0,
    ///         move |move_dir| pareen::prop(move_dir) * move_speed,
    ///     )
    /// }
    ///
    /// let move_anim = my_offset_anim(Some(1.0));
    /// let stay_anim = my_offset_anim(None);
    ///
    /// assert_approx_eq!(move_anim.eval(0.5), 1.0);
    /// assert_approx_eq!(stay_anim.eval(0.5), 0.0);
    /// ```
    pub fn map_or<W, G, H, A>(
        self,
        default: A,
        f: impl Fn(V) -> Anim<H>,
    ) -> Anim<impl Fun<T = F::T, V = W>>
    where
        G: Fun<T = F::T, V = W>,
        H: Fun<T = F::T, V = W>,
        A: Into<Anim<G>>,
    {
        let default = default.into();

        //self.bind(move |v| v.map_or(default, f))

        fun(move |t: F::T| {
            self.eval(t.clone())
                .map_or_else(|| default.eval(t.clone()), |v| f(v).eval(t.clone()))
        })
    }
}

/// Return the value of one of two animations depending on a condition.
///
/// This allows returning animations of different types conditionally.
///
/// Note that the condition `cond` may either be a value `true` and `false`, or
/// it may itself be a dynamic animation of type `bool`.
///
/// For dynamic conditions, in many cases it suffices to use either
/// [`Anim::switch`](struct.Anim.html#method.switch) or
/// [`Anim::seq`](struct.Anim.html#method.seq) instead of this function.
///
/// # Examples
/// ## Constant conditions
///
/// The following example does _not_ compile, because the branches have
/// different types:
/// ```compile_fail
/// let cond = true;
/// let anim = if cond { pareen::constant(1) } else { pareen::id() };
/// ```
///
/// However, this does compile:
/// ```
/// let cond = true;
/// let anim = pareen::cond(cond, 1, pareen::id());
///
/// assert_eq!(anim.eval(2), 1);
/// ```
///
/// ## Dynamic conditions
///
/// ```
/// let cond = pareen::fun(|t| t * t <= 4);
/// let anim_1 = 1;
/// let anim_2 = pareen::id();
/// let anim = pareen::cond(cond, anim_1, anim_2);
///
/// assert_eq!(anim.eval(1), 1); // 1 * 1 <= 4
/// assert_eq!(anim.eval(2), 1); // 2 * 2 <= 4
/// assert_eq!(anim.eval(3), 3); // 3 * 3 > 4
/// ```
pub fn cond<F, G, H, Cond, A, B>(cond: Cond, a: A, b: B) -> Anim<impl Fun<T = F::T, V = G::V>>
where
    F::T: Clone,
    F: Fun<V = bool>,
    G: Fun<T = F::T>,
    H: Fun<T = F::T, V = G::V>,
    Cond: Into<Anim<F>>,
    A: Into<Anim<G>>,
    B: Into<Anim<H>>,
{
    // Nested closures result in exponential compilation time increase, and we
    // expect cond to be used often. Thus, we avoid using `pareen::fun` here.
    // For reference: https://github.com/rust-lang/rust/issues/72408
    Anim(CondClosure(cond.into().0, a.into().0, b.into().0))
}

#[doc(hidden)]
#[derive(Debug, Clone)]
pub struct CondClosure<F, G, H>(F, G, H);

impl<F, G, H> Fun for CondClosure<F, G, H>
where
    F::T: Clone,
    F: Fun<V = bool>,
    G: Fun<T = F::T>,
    H: Fun<T = F::T, V = G::V>,
{
    type T = F::T;
    type V = G::V;

    fn eval(&self, t: F::T) -> G::V {
        if self.0.eval(t.clone()) {
            self.1.eval(t)
        } else {
            self.2.eval(t)
        }
    }
}

/// Linearly interpolate between two animations, starting at time zero and
/// finishing at time one.
///
/// This is a wrapper around [`Anim::lerp`](struct.Anim.html#method.lerp) for
/// convenience, allowing automatic conversion into [`Anim`](struct.Anim.html)
/// for both `a` and `b`.
///
/// # Example
///
/// Linearly interpolate between two constant values:
///
/// ```
/// # use assert_approx_eq::assert_approx_eq;
/// let anim = pareen::lerp(5.0f32, 10.0);
///
/// assert_approx_eq!(anim.eval(0.0f32), 5.0);
/// assert_approx_eq!(anim.eval(0.5), 7.5);
/// assert_approx_eq!(anim.eval(1.0), 10.0);
/// assert_approx_eq!(anim.eval(2.0), 15.0);
/// ```
pub fn lerp<T, V, W, F, G, A, B>(a: A, b: B) -> Anim<impl Fun<T = T, V = V>>
where
    T: Copy + Mul<W, Output = W>,
    V: Copy + Add<W, Output = V> + Sub<Output = W>,
    F: Fun<T = T, V = V>,
    G: Fun<T = T, V = V>,
    A: Into<Anim<F>>,
    B: Into<Anim<G>>,
{
    a.into().lerp(b.into())
}

/// Build an animation that depends on matching some expression.
///
/// Importantly, this macro allows returning animations of a different type in
/// each match arm, which is not possible with a normal `match` expression.
///
/// # Example
/// ```
/// # use assert_approx_eq::assert_approx_eq;
/// enum MyPlayerState {
///     Standing,
///     Running,
///     Jumping,
/// }
///
/// fn my_anim(state: MyPlayerState) -> pareen::Anim<impl pareen::Fun<T = f64, V = f64>> {
///     pareen::anim_match!(state;
///         MyPlayerState::Standing => pareen::constant(0.0),
///         MyPlayerState::Running => pareen::prop(1.0),
///         MyPlayerState::Jumping => pareen::id().powi(2),
///     )
/// }
///
/// assert_approx_eq!(my_anim(MyPlayerState::Standing).eval(2.0), 0.0);
/// assert_approx_eq!(my_anim(MyPlayerState::Running).eval(2.0), 2.0);
/// assert_approx_eq!(my_anim(MyPlayerState::Jumping).eval(2.0), 4.0);
/// ```
#[macro_export]
macro_rules! anim_match {
    (
        $expr:expr;
        $($pat:pat => $value:expr $(,)?)*
    ) => {
        $crate::fun(move |t| match $expr {
            $(
                $pat => ($crate::Anim::from($value)).eval(t),
            )*
        })
    }
}

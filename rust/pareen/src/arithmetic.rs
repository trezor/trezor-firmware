use core::ops::{Add, Mul, Neg, Sub};

use crate::{primitives::ConstantClosure, Anim, Fun};

impl<F, G> Add<Anim<G>> for Anim<F>
where
    F: Fun,
    G: Fun<T = F::T>,
    F::V: Add<G::V>,
{
    type Output = Anim<AddClosure<F, G>>;

    fn add(self, rhs: Anim<G>) -> Self::Output {
        Anim(AddClosure(self.0, rhs.0))
    }
}

impl<W, F> Add<W> for Anim<F>
where
    W: Copy,
    F: Fun,
    F::V: Add<W>,
{
    type Output = Anim<AddClosure<F, ConstantClosure<F::T, W>>>;

    fn add(self, rhs: W) -> Self::Output {
        Anim(AddClosure(self.0, ConstantClosure::from(rhs)))
    }
}

impl<F, G> Sub<Anim<G>> for Anim<F>
where
    F: Fun,
    G: Fun<T = F::T>,
    F::V: Sub<G::V>,
{
    type Output = Anim<SubClosure<F, G>>;

    fn sub(self, rhs: Anim<G>) -> Self::Output {
        Anim(SubClosure(self.0, rhs.0))
    }
}

impl<W, F> Sub<W> for Anim<F>
where
    W: Copy,
    F: Fun,
    F::T: Copy,
    F::V: Sub<W>,
{
    type Output = Anim<SubClosure<F, ConstantClosure<F::T, W>>>;

    fn sub(self, rhs: W) -> Self::Output {
        Anim(SubClosure(self.0, ConstantClosure::from(rhs)))
    }
}

impl<F, G> Mul<Anim<G>> for Anim<F>
where
    F: Fun,
    G: Fun<T = F::T>,
    F::T: Copy,
    F::V: Mul<G::V>,
{
    type Output = Anim<MulClosure<F, G>>;

    fn mul(self, rhs: Anim<G>) -> Self::Output {
        Anim(MulClosure(self.0, rhs.0))
    }
}

impl<W, F> Mul<W> for Anim<F>
where
    W: Copy,
    F: Fun,
    F::T: Copy,
    F::V: Mul<W>,
{
    type Output = Anim<MulClosure<F, ConstantClosure<F::T, W>>>;

    fn mul(self, rhs: W) -> Self::Output {
        Anim(MulClosure(self.0, ConstantClosure::from(rhs)))
    }
}

impl<V, F> Neg for Anim<F>
where
    V: Copy,
    F: Fun<V = V>,
{
    type Output = Anim<NegClosure<F>>;

    fn neg(self) -> Self::Output {
        Anim(NegClosure(self.0))
    }
}

#[doc(hidden)]
#[derive(Debug, Clone)]
pub struct AddClosure<F, G>(F, G);

impl<F, G> Fun for AddClosure<F, G>
where
    F: Fun,
    G: Fun<T = F::T>,
    F::T: Clone,
    F::V: Add<G::V>,
{
    type T = F::T;
    type V = <F::V as Add<G::V>>::Output;

    fn eval(&self, t: F::T) -> Self::V {
        self.0.eval(t.clone()) + self.1.eval(t)
    }
}

#[doc(hidden)]
#[derive(Debug, Clone)]
pub struct SubClosure<F, G>(F, G);

impl<F, G> Fun for SubClosure<F, G>
where
    F: Fun,
    G: Fun<T = F::T>,
    F::T: Clone,
    F::V: Sub<G::V>,
{
    type T = F::T;
    type V = <F::V as Sub<G::V>>::Output;

    fn eval(&self, t: F::T) -> Self::V {
        self.0.eval(t.clone()) - self.1.eval(t)
    }
}

#[doc(hidden)]
#[derive(Debug, Clone)]
pub struct MulClosure<F, G>(F, G);

impl<F, G> Fun for MulClosure<F, G>
where
    F: Fun,
    G: Fun<T = F::T>,
    F::T: Copy,
    F::V: Mul<G::V>,
{
    type T = F::T;
    type V = <F::V as Mul<G::V>>::Output;

    fn eval(&self, t: F::T) -> Self::V {
        self.0.eval(t) * self.1.eval(t)
    }
}

#[doc(hidden)]
pub struct NegClosure<F>(F);

impl<F> Fun for NegClosure<F>
where
    F: Fun,
    F::V: Neg,
{
    type T = F::T;
    type V = <F::V as Neg>::Output;

    fn eval(&self, t: F::T) -> Self::V {
        -self.0.eval(t)
    }
}

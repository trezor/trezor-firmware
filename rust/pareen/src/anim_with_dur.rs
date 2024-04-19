use core::ops::{Add, Div, Mul, Sub};

use num_traits::{float::FloatCore, One};

use crate::{Anim, Fun};

/// An `Anim` together with the duration that it is intended to be played for.
///
/// Explicitly carrying the duration around makes it easier to sequentially
/// compose animations in some places.
#[derive(Clone, Debug)]
pub struct AnimWithDur<F: Fun>(pub Anim<F>, pub F::T);

impl<F> Anim<F>
where
    F: Fun,
{
    /// Tag this animation with the duration that it is intended to be played
    /// for.
    ///
    /// Note that using this tagging is completely optional, but it may
    /// make it easier to combine animations sometimes.
    pub fn dur(self, t: F::T) -> AnimWithDur<F> {
        AnimWithDur(self, t)
    }
}

impl<'a, V> From<&'a [V]> for AnimWithDur<SliceClosure<'a, V>>
where
    V: Clone,
{
    fn from(slice: &'a [V]) -> Self {
        AnimWithDur(Anim(SliceClosure(slice)), slice.len())
    }
}

pub fn slice<'a, V>(slice: &'a [V]) -> AnimWithDur<impl Fun<T = usize, V = V> + 'a>
where
    V: Clone + 'a,
{
    slice.into()
}

#[doc(hidden)]
pub struct SliceClosure<'a, V>(&'a [V]);

impl<'a, V> Fun for SliceClosure<'a, V>
where
    V: Clone,
{
    type T = usize;
    type V = V;

    fn eval(&self, t: Self::T) -> Self::V {
        self.0[t].clone()
    }
}

impl<F> Anim<F>
where
    F: Fun,
    F::T: Clone + FloatCore,
{
    pub fn scale_to_dur(self, dur: F::T) -> AnimWithDur<impl Fun<T = F::T, V = F::V>> {
        self.scale_time(F::T::one() / dur).dur(dur)
    }
}

impl<F> AnimWithDur<F>
where
    F: Fun,
    F::T: Clone,
{
    pub fn as_ref(&self) -> AnimWithDur<&F> {
        AnimWithDur(self.0.as_ref(), self.1.clone())
    }
}

impl<F> AnimWithDur<F>
where
    F: Fun,
{
    pub fn transform<G, H>(self, h: H) -> AnimWithDur<G>
    where
        G: Fun<T = F::T>,
        H: FnOnce(Anim<F>) -> Anim<G>,
    {
        AnimWithDur(h(self.0), self.1)
    }

    pub fn map<W>(self, f: impl Fn(F::V) -> W) -> AnimWithDur<impl Fun<T = F::T, V = W>> {
        self.transform(move |anim| anim.map(f))
    }

    pub fn dur(self, t: F::T) -> AnimWithDur<F> {
        AnimWithDur(self.0, t)
    }
}

impl<'a, T, X, Y, F> AnimWithDur<F>
where
    T: 'a + Clone,
    X: 'a,
    Y: 'a,
    F: Fun<T = T, V = (X, Y)>,
{
    pub fn unzip(
        &'a self,
    ) -> (
        AnimWithDur<impl Fun<T = F::T, V = X> + 'a>,
        AnimWithDur<impl Fun<T = F::T, V = Y> + 'a>,
    ) {
        (
            self.as_ref().transform(|anim| anim.fst()),
            self.as_ref().transform(|anim| anim.snd()),
        )
    }
}

impl<F> AnimWithDur<F>
where
    F: Fun,
    F::T: Copy + PartialOrd + Sub<Output = F::T>,
{
    pub fn seq<G>(self, next: Anim<G>) -> Anim<impl Fun<T = F::T, V = F::V>>
    where
        G: Fun<T = F::T, V = F::V>,
    {
        self.0.seq(self.1, next)
    }
}

impl<F> AnimWithDur<F>
where
    F: Fun,
    F::T: Copy + PartialOrd + Sub<Output = F::T> + Add<Output = F::T>,
{
    pub fn seq_with_dur<G>(self, next: AnimWithDur<G>) -> AnimWithDur<impl Fun<T = F::T, V = F::V>>
    where
        G: Fun<T = F::T, V = F::V>,
    {
        let dur = self.1.clone() + next.1;
        AnimWithDur(self.seq(next.0), dur)
    }
}

impl<F> AnimWithDur<F>
where
    F: Fun,
    F::T: Clone + FloatCore,
{
    pub fn repeat(self) -> Anim<impl Fun<T = F::T, V = F::V>> {
        self.0.repeat(self.1)
    }
}

impl<F> AnimWithDur<F>
where
    F: Fun,
    F::T: Clone + Sub<Output = F::T>,
{
    pub fn backwards(self) -> AnimWithDur<impl Fun<T = F::T, V = F::V>> {
        AnimWithDur(self.0.backwards(self.1.clone()), self.1)
    }
}

impl<F> AnimWithDur<F>
where
    F: Fun,
    F::T: Clone + Mul<Output = F::T> + Div<Output = F::T>,
{
    pub fn scale_time(self, t_scale: F::T) -> AnimWithDur<impl Fun<T = F::T, V = F::V>> {
        AnimWithDur(self.0.scale_time(t_scale.clone()), self.1 / t_scale)
    }
}

#[macro_export]
macro_rules! seq_with_dur {
    (
        $expr:expr $(,)?
    ) => {
        $expr
    };

    (
        $head:expr,
        $($tail:expr $(,)?)+
    ) => {
        $head.seq_with_dur($crate::seq_with_dur!($($tail,)*))
    }
}

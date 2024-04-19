use core::ops::{Deref, Sub};
extern crate alloc;
use alloc::boxed::Box;

use crate::{Anim, Fun};

pub type AnimBox<T, V> = Anim<Box<dyn Fun<T = T, V = V>>>;

impl<F> Anim<F>
where
    F: Fun + 'static,
{
    /// Returns a boxed version of this animation.
    ///
    /// This may be used to reduce the compilation time of deeply nested
    /// animations.
    pub fn into_box(self) -> AnimBox<F::T, F::V> {
        Anim(Box::new(self.0))
    }

    pub fn into_box_fn(self) -> Box<dyn Fn(F::T) -> F::V> {
        Box::new(self.into_fn())
    }
}

// TODO: We need to get rid of the 'static requirements.
impl<F> Anim<F>
where
    F: Fun + 'static,
    F::T: Copy + PartialOrd + Sub<Output = F::T> + 'static,
    F::V: 'static,
{
    pub fn seq_box<G, A>(self, self_end: F::T, next: A) -> AnimBox<F::T, F::V>
    where
        G: Fun<T = F::T, V = F::V> + 'static,
        A: Into<Anim<G>>,
    {
        self.into_box()
            .seq(self_end, next.into().into_box())
            .into_box()
    }
}

impl<'a, T, V> Fun for Box<dyn Fun<T = T, V = V>> {
    type T = T;
    type V = V;

    fn eval(&self, t: Self::T) -> Self::V {
        self.deref().eval(t)
    }
}

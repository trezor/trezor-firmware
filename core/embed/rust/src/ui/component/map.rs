use super::{Component, Event, EventCtx};

pub struct Map<T, F> {
    inner: T,
    func: F,
}

impl<T, F> Map<T, F> {
    pub fn new(inner: T, func: F) -> Self {
        Self { inner, func }
    }
}

impl<T, F, U> Component for Map<T, F>
where
    T: Component,
    F: Fn(T::Msg) -> U,
{
    type Msg = U;

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.inner.event(ctx, event).map(&self.func)
    }

    fn paint(&mut self) {
        self.inner.paint()
    }
}

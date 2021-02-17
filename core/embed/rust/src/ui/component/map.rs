use super::{component::Widget, Component, Event, EventCtx};

pub struct Map<T, F> {
    inner: T,
    map_fn: F,
}

impl<T, F> Map<T, F> {
    pub fn new(inner: T, map_fn: F) -> Self {
        Self { inner, map_fn }
    }
}

impl<T, F, M> Component for Map<T, F>
where
    T: Component,
    F: FnMut(T::Msg) -> M,
{
    type Msg = M;

    fn widget(&mut self) -> &mut Widget {
        self.inner.widget()
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.inner.event(ctx, event).map(&mut self.map_fn)
    }

    fn paint(&mut self) {
        self.inner.paint()
    }
}

use super::{Component, Event, EventCtx};
use crate::ui::geometry::Rect;

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
    F: Fn(T::Msg) -> Option<U>,
{
    type Msg = U;

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.inner.event(ctx, event).and_then(&self.func)
    }

    fn paint(&mut self) {
        self.inner.paint()
    }

    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        self.inner.bounds(sink);
    }
}

#[cfg(feature = "ui_debug")]
impl<T, F> crate::trace::Trace for Map<T, F>
where
    T: Component + crate::trace::Trace,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        self.inner.trace(t)
    }
}

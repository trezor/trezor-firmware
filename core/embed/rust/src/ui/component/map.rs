use super::{Component, Event, EventCtx};
use crate::ui::{geometry::Rect, shape::Renderer};

pub struct MsgMap<T, F> {
    inner: T,
    func: F,
}

impl<T, F> MsgMap<T, F> {
    pub fn new(inner: T, func: F) -> Self {
        Self { inner, func }
    }
}

impl<T, F, U> Component for MsgMap<T, F>
where
    T: Component,
    F: Fn(T::Msg) -> Option<U>,
{
    type Msg = U;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.inner.place(bounds)
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.inner.event(ctx, event).and_then(&self.func)
    }

    fn paint(&mut self) {
        self.inner.paint()
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.inner.render(target);
    }

    #[cfg(feature = "ui_bounds")]
    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        self.inner.bounds(sink);
    }
}

#[cfg(feature = "ui_debug")]
impl<T, F> crate::trace::Trace for MsgMap<T, F>
where
    T: Component + crate::trace::Trace,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        self.inner.trace(t)
    }
}

#[cfg(all(feature = "micropython", feature = "touch"))]
impl<T, F> crate::ui::flow::Swipable for MsgMap<T, F>
where
    T: Component + crate::ui::flow::Swipable,
{
    fn swipe_start(&mut self, ctx: &mut EventCtx, direction: super::SwipeDirection) -> bool {
        self.inner.swipe_start(ctx, direction)
    }

    fn swipe_finished(&self) -> bool {
        self.inner.swipe_finished()
    }
}

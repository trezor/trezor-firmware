use super::{Component, Event, EventCtx};
use crate::ui::geometry::Rect;

impl<T, A, B> Component for (A, B)
where
    A: Component<Msg = T>,
    B: Component<Msg = T>,
{
    type Msg = T;

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.0
            .event(ctx, event)
            .or_else(|| self.1.event(ctx, event))
    }

    fn paint(&mut self) {
        self.0.paint();
        self.1.paint();
    }

    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        self.0.bounds(sink);
        self.1.bounds(sink);
    }
}

impl<T, A, B, C> Component for (A, B, C)
where
    A: Component<Msg = T>,
    B: Component<Msg = T>,
    C: Component<Msg = T>,
{
    type Msg = T;

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.0
            .event(ctx, event)
            .or_else(|| self.1.event(ctx, event))
            .or_else(|| self.2.event(ctx, event))
    }

    fn paint(&mut self) {
        self.0.paint();
        self.1.paint();
        self.2.paint();
    }

    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        self.0.bounds(sink);
        self.1.bounds(sink);
        self.2.bounds(sink);
    }
}

#[cfg(feature = "ui_debug")]
impl<T, A, B> crate::trace::Trace for (A, B)
where
    A: Component<Msg = T> + crate::trace::Trace,
    B: Component<Msg = T> + crate::trace::Trace,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.open("Tuple");
        t.field("0", &self.0);
        t.field("1", &self.1);
        t.close();
    }
}

#[cfg(feature = "ui_debug")]
impl<T, A, B, C> crate::trace::Trace for (A, B, C)
where
    A: Component<Msg = T> + crate::trace::Trace,
    B: Component<Msg = T> + crate::trace::Trace,
    C: Component<Msg = T> + crate::trace::Trace,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.open("Tuple");
        t.field("0", &self.0);
        t.field("1", &self.1);
        t.field("2", &self.2);
        t.close();
    }
}

use super::{Component, Event, EventCtx, Never};
use crate::ui::geometry::Rect;

pub struct Empty;

impl Component for Empty {
    type Msg = Never;

    fn place(&mut self, _bounds: Rect) -> Rect {
        Rect::zero()
    }

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    fn paint(&mut self) {}
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for Empty {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.open("Empty");
        t.close();
    }
}

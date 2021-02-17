use crate::ui::math::{Offset, Point, Rect};

use super::component::{Component, Event, EventCtx, Widget};

pub struct Empty {
    widget: Widget,
}

impl Empty {
    pub fn new() -> Self {
        Self {
            widget: Widget::new(Rect::with_size(Point::zero(), Offset::zero())),
        }
    }
}

impl Component for Empty {
    type Msg = !;

    fn widget(&mut self) -> &mut Widget {
        &mut self.widget
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        None
    }

    fn paint(&mut self) {}
}

use crate::ui::{
    component::{Component, Event, EventCtx, Label},
    geometry::Rect,
    shape::Renderer,
};

use super::HomescreenMsg;

pub struct Lockscreen {
    label: Label<'static>,
}

impl Component for Lockscreen {
    type Msg = HomescreenMsg;
    fn place(&mut self, bounds: Rect) -> Rect {
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {}
}

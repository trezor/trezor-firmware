use crate::ui::component::{Component, Event, EventCtx, Never};

pub struct Empty;

impl Component for Empty {
    type Msg = Never;

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    fn paint(&mut self) {}
}

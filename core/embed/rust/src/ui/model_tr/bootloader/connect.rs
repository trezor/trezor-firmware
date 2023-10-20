use crate::ui::{
    component::{Component, Event, EventCtx, Never, Pad},
    display::{self, Font},
    geometry::{Offset, Rect},
};

use super::super::theme::bootloader::{BLD_BG, BLD_FG};

pub struct Connect {
    bg: Pad,
    message: &'static str,
}

impl Connect {
    pub fn new(message: &'static str) -> Self {
        Self {
            bg: Pad::with_background(BLD_BG).with_clear(),
            message,
        }
    }
}

impl Component for Connect {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.bg.place(bounds);
        bounds
    }

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    fn paint(&mut self) {
        let font = Font::NORMAL;

        self.bg.paint();
        display::text_center(
            self.bg.area.center() + Offset::y(font.text_height() / 2),
            self.message,
            font,
            BLD_FG,
            BLD_BG,
        );
    }
}

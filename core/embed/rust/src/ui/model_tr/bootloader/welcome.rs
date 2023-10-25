use crate::ui::{
    component::{Component, Event, EventCtx, Never, Pad},
    display::{self, Font},
    geometry::{Offset, Rect},
};

use super::super::theme::bootloader::{BLD_BG, BLD_FG};

pub struct Welcome {
    bg: Pad,
}

impl Welcome {
    pub fn new() -> Self {
        Self {
            bg: Pad::with_background(BLD_BG).with_clear(),
        }
    }
}

impl Component for Welcome {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.bg.place(bounds);
        bounds
    }

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    fn paint(&mut self) {
        self.bg.paint();

        let top_center = self.bg.area.top_center();

        display::text_center(
            top_center + Offset::y(24),
            "Get started with",
            Font::NORMAL,
            BLD_FG,
            BLD_BG,
        );
        display::text_center(
            top_center + Offset::y(32),
            "your Trezor at",
            Font::NORMAL,
            BLD_FG,
            BLD_BG,
        );
        display::text_center(
            top_center + Offset::y(48),
            "trezor.io/start",
            Font::BOLD,
            BLD_FG,
            BLD_BG,
        );
    }
}

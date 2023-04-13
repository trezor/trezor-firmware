use crate::ui::{
    component::{Component, Event, EventCtx, Never, Pad},
    constant::screen,
    display::{self, Font},
    geometry::{Offset, Rect},
    model_tr::bootloader::theme::{BLD_BG, BLD_FG},
};

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
        self.bg.place(screen());
        bounds
    }

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    fn paint(&mut self) {
        self.bg.paint();
        display::text_center(
            screen().top_center() + Offset::y(20),
            "Get started with",
            Font::NORMAL,
            BLD_FG,
            BLD_BG,
        );
        display::text_center(
            screen().top_center() + Offset::y(35),
            "your Trezor at",
            Font::NORMAL,
            BLD_FG,
            BLD_BG,
        );
        display::text_center(
            screen().top_center() + Offset::y(50),
            "trezor.io/start",
            Font::BOLD,
            BLD_FG,
            BLD_BG,
        );
    }
}

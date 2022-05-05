use crate::ui::{
    component::{Component, Event, EventCtx, Never, Pad},
    constant::screen,
    display::{self, Font},
    geometry::{Offset, Rect},
    model_tt::bootloader::theme::{BLD_BG, BLD_TITLE_COLOR},
};

pub struct Connect {
    bg: Pad,
    message: &'static str,
}

impl Connect {
    pub fn new(message: &'static str) -> Self {
        let mut instance = Self {
            bg: Pad::with_background(BLD_BG),
            message,
        };

        instance.bg.clear();
        instance
    }
}

impl Component for Connect {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.bg.place(screen());
        bounds
    }

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    fn paint(&mut self) {
        let font = Font::NORMAL;

        self.bg.paint();
        display::text_center(
            screen().center() + Offset::y(font.text_height() / 2),
            self.message,
            Font::NORMAL,
            BLD_TITLE_COLOR,
            BLD_BG,
        );
    }
}

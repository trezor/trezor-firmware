use crate::ui::{
    component::{Component, Event, EventCtx, Never, Pad},
    constant::screen,
    display::{self, Color, Font},
    geometry::{Offset, Rect},
    model_tt::theme::bootloader::BLD_TITLE_COLOR,
};

pub struct Connect {
    bg: Pad,
    message: &'static str,
}

impl Connect {
    pub fn new(message: &'static str, bg: Color) -> Self {
        let mut instance = Self {
            bg: Pad::with_background(bg),
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
            self.bg.color,
        );
    }
}

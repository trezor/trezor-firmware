use crate::ui::{
    component::{Component, Event, EventCtx, Never, Pad},
    constant::screen,
    display::{self, Font},
    geometry::{Offset, Point, Rect},
};

use super::super::theme::{BLACK, GREY, WHITE};

const TEXT_ORIGIN: Point = Point::new(0, 105);
const STRIDE: i16 = 22;

pub struct Welcome {
    bg: Pad,
}

impl Welcome {
    pub fn new() -> Self {
        Self {
            bg: Pad::with_background(BLACK).with_clear(),
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
        let at_width = Font::NORMAL.text_width("at ");

        self.bg.paint();
        display::text_left(TEXT_ORIGIN, "Get started", Font::NORMAL, GREY, BLACK);
        display::text_left(
            TEXT_ORIGIN + Offset::y(STRIDE),
            "with your Trezor",
            Font::NORMAL,
            GREY,
            BLACK,
        );
        display::text_left(
            TEXT_ORIGIN + Offset::y(2 * STRIDE),
            "at",
            Font::NORMAL,
            GREY,
            BLACK,
        );
        display::text_left(
            TEXT_ORIGIN + Offset::new(at_width, 2 * STRIDE),
            "trezor.io/start",
            Font::NORMAL,
            WHITE,
            BLACK,
        );
    }
}

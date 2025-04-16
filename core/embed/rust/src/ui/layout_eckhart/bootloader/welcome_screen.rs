use crate::ui::{
    component::{Component, Event, EventCtx, Never, Pad},
    constant::screen,
    geometry::{Offset, Point, Rect},
    shape,
    shape::Renderer,
};

use super::super::{
    fonts,
    theme::{BLACK, GREY, WHITE},
};

// TODO: adjust the origin
const TEXT_ORIGIN: Point = Point::new(24, 205);
const STRIDE: i16 = 38;

/// Bootloader welcome screen
pub struct BldWelcomeScreen {
    bg: Pad,
}

impl BldWelcomeScreen {
    pub fn new() -> Self {
        Self {
            bg: Pad::with_background(BLACK).with_clear(),
        }
    }
}

impl Component for BldWelcomeScreen {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.bg.place(screen());
        bounds
    }

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.bg.render(target);
        let font = fonts::FONT_SATOSHI_REGULAR_38;
        shape::Text::new(TEXT_ORIGIN, "Get started", font)
            .with_fg(GREY)
            .render(target);

        shape::Text::new(TEXT_ORIGIN + Offset::y(STRIDE), "with your Trezor", font)
            .with_fg(GREY)
            .render(target);

        shape::Text::new(TEXT_ORIGIN + Offset::y(2 * STRIDE), "at", font)
            .with_fg(GREY)
            .render(target);

        let at_width = font.text_width("at ");

        shape::Text::new(
            TEXT_ORIGIN + Offset::new(at_width, 2 * STRIDE),
            "trezor.io/start",
            font,
        )
        .with_fg(WHITE)
        .render(target);
    }
}

use crate::ui::{
    component::{Component, Event, EventCtx, Never, Pad},
    constant::screen,
    geometry::{Offset, Point, Rect},
    shape::{self, Renderer},
};

use super::{
    super::theme::{BLACK, GREY, WHITE},
    fonts,
};

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

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.bg.render(target);
        let font = fonts::FONT_DEMIBOLD;

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

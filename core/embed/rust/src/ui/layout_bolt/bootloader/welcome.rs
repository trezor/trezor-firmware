use crate::ui::{
    component::{Component, Event, EventCtx, Never, Pad},
    constant::screen,
    display::{toif::Toif, Font},
    geometry::{Alignment, Alignment2D, Offset, Rect},
    shape,
    shape::Renderer,
};

use super::super::theme::{
    bootloader::{START_URL, WELCOME_COLOR},
    GREY_MEDIUM, WHITE,
};

pub struct Welcome {
    bg: Pad,
}

impl Welcome {
    pub fn new() -> Self {
        Self {
            bg: Pad::with_background(WELCOME_COLOR).with_clear(),
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

        shape::Text::new(screen().top_center() + Offset::y(102), "Get started with")
            .with_align(Alignment::Center)
            .with_font(Font::NORMAL)
            .with_fg(GREY_MEDIUM)
            .render(target);

        shape::Text::new(screen().top_center() + Offset::y(126), "your Trezor at")
            .with_align(Alignment::Center)
            .with_font(Font::NORMAL)
            .with_fg(GREY_MEDIUM)
            .render(target);

        let icon = unwrap!(Toif::new(START_URL));
        shape::ToifImage::new(screen().top_center() + Offset::y(135), icon)
            .with_align(Alignment2D::TOP_CENTER)
            .with_fg(WHITE)
            .render(target);
    }
}

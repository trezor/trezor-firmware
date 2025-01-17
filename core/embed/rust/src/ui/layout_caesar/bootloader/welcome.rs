use crate::ui::{
    component::{Component, Event, EventCtx, Never, Pad},
    display::Font,
    geometry::{Alignment, Offset, Rect},
    shape,
    shape::Renderer,
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

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.bg.render(target);

        let top_center = self.bg.area.top_center();

        shape::Text::new(top_center + Offset::y(24), "Get started with")
            .with_align(Alignment::Center)
            .with_font(Font::NORMAL)
            .with_fg(BLD_FG)
            .render(target);

        shape::Text::new(top_center + Offset::y(32), "your Trezor at")
            .with_align(Alignment::Center)
            .with_font(Font::NORMAL)
            .with_fg(BLD_FG)
            .render(target);

        shape::Text::new(top_center + Offset::y(48), "trezor.io/start")
            .with_align(Alignment::Center)
            .with_font(Font::BOLD)
            .with_fg(BLD_FG)
            .render(target);
    }
}

use crate::ui::{
    component::{Component, Event, EventCtx, Never},
    geometry::{Alignment, Offset, Rect},
    shape,
    shape::Renderer,
};

use super::super::{
    fonts,
    theme::{GREY_LIGHT, TEXT_VERTICAL_SPACING},
};

const TEXT_OFFSET: Offset = Offset::new(30, 40);

/// Firmware welcome screen
pub struct WelcomeScreen {
    area: Rect,
}

impl WelcomeScreen {
    pub fn new() -> Self {
        Self { area: Rect::zero() }
    }
}

impl Component for WelcomeScreen {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.area = bounds;
        self.area
    }

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        // TODO: should we use `model::FULL_NAME`?

        const NAME_PARTS: [&str; 3] = ["Trezor", "Safe", "5"];

        let font = fonts::FONT_SATOSHI_REGULAR_38;
        let mut cursor = self.area.top_left() + TEXT_OFFSET;
        let row_height = font.text_height() + TEXT_VERTICAL_SPACING;

        for part in &NAME_PARTS {
            shape::Text::new(cursor, part, font)
                .with_align(Alignment::Start)
                .with_fg(GREY_LIGHT)
                .render(target);
            cursor = cursor + Offset::y(row_height);
        }
    }
}

#[cfg(not(feature = "bootloader"))]
use crate::trezorhal::model;
#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for WelcomeScreen {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("WelcomeScreen");
        #[cfg(not(feature = "bootloader"))]
        t.string("model", model::FULL_NAME.into());
    }
}

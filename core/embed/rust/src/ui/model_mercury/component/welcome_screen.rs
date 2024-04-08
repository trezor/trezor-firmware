use crate::ui::{
    component::{Component, Event, EventCtx, Never},
    display,
    geometry::{Alignment2D, Offset, Rect},
};

use super::theme;

const TEXT_BOTTOM_MARGIN: i16 = 54;
const ICON_TOP_MARGIN: i16 = 48;
#[cfg(not(feature = "bootloader"))]
const MODEL_NAME_FONT: display::Font = display::Font::DEMIBOLD;
#[cfg(not(feature = "bootloader"))]
use crate::trezorhal::model;

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

    fn paint(&mut self) {
        theme::ICON_LOGO.draw(
            self.area.top_center() + Offset::y(ICON_TOP_MARGIN),
            Alignment2D::TOP_CENTER,
            theme::FG,
            theme::BG,
        );
        display::text_center(
            self.area.bottom_center() - Offset::y(TEXT_BOTTOM_MARGIN),
            "Trezor Safe 5",
            display::Font::NORMAL,
            theme::FG,
            theme::BG,
        );
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for WelcomeScreen {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("WelcomeScreen");
        #[cfg(not(feature = "bootloader"))]
        t.string("model", model::FULL_NAME.into());
    }
}

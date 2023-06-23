use crate::ui::{
    component::{Component, Event, EventCtx, Never},
    geometry::{Alignment2D, Offset, Rect},
    model_tt::theme,
};
#[cfg(feature = "bootloader")]
use crate::ui::{display::Icon, model_tt::bootloader::theme::DEVICE_NAME};

const TEXT_BOTTOM_MARGIN: i16 = 24; // matching the homescreen label margin
const ICON_TOP_MARGIN: i16 = 48;
#[cfg(not(feature = "bootloader"))]
const MODEL_NAME_FONT: display::Font = display::Font::DEMIBOLD;
#[cfg(not(feature = "bootloader"))]
use crate::ui::{constant::MODEL_NAME, display};

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
        #[cfg(not(feature = "bootloader"))]
        display::text_center(
            self.area.bottom_center() - Offset::y(TEXT_BOTTOM_MARGIN),
            MODEL_NAME,
            MODEL_NAME_FONT,
            theme::FG,
            theme::BG,
        );
        #[cfg(feature = "bootloader")]
        Icon::new(DEVICE_NAME).draw(
            self.area.bottom_center() - Offset::y(TEXT_BOTTOM_MARGIN) + Offset::y(1),
            Alignment2D::BOTTOM_CENTER,
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
        t.string("model", MODEL_NAME);
    }
}

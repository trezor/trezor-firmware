use crate::ui::{
    component::{Component, Event, EventCtx, Never},
    geometry::{Alignment2D, Offset, Rect},
};

use super::super::theme;

const ICON_TOP_MARGIN: i16 = 11;

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
        theme::ICON_DEVICE_NAME.draw(
            self.area.bottom_center(),
            Alignment2D::BOTTOM_CENTER,
            theme::FG,
            theme::BG,
        );
        theme::ICON_LOGO.draw(
            self.area.top_center() + Offset::y(ICON_TOP_MARGIN),
            Alignment2D::TOP_CENTER,
            theme::FG,
            theme::BG,
        );
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for WelcomeScreen {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("WelcomeScreen");
        t.string("model_name", "Trezor Model R");
    }
}

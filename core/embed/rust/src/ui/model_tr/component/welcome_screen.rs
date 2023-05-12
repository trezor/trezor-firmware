use crate::ui::{
    component::{Component, Event, EventCtx, Never},
    constant::MODEL_NAME,
    display,
    geometry::{self, Offset, Rect},
};

use super::super::theme;

const TEXT_BOTTOM_MARGIN: i16 = 2; // matching the homescreen label margin
const ICON_TOP_MARGIN: i16 = 11;
const MODEL_NAME_FONT: display::Font = display::Font::NORMAL;

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
        display::text_center(
            self.area.bottom_center() - Offset::y(TEXT_BOTTOM_MARGIN),
            MODEL_NAME,
            MODEL_NAME_FONT,
            theme::FG,
            theme::BG,
        );
        theme::ICON_LOGO.draw(
            self.area.top_center() + Offset::y(ICON_TOP_MARGIN),
            geometry::TOP_CENTER,
            theme::FG,
            theme::BG,
        );
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for WelcomeScreen {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("WelcomeScreen");
        t.string("model_name", MODEL_NAME);
    }
}

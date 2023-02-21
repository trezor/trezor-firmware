use crate::ui::{
    component::{Component, Event, EventCtx, Never},
    display::{self, Icon},
    geometry::{self, Offset, Rect},
    model_tt::theme,
};

const TEXT_BOTTOM_MARGIN: i16 = 24; // matching the homescreen label margin
const ICON_TOP_MARGIN: i16 = 62;
const MODEL_NAME: &str = "Trezor Model T";
const MODEL_NAME_FONT: display::Font = display::Font::DEMIBOLD;

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
        Icon::new(theme::ICON_LOGO).draw(
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
        t.open("WelcomeScreen");
        t.string(MODEL_NAME);
        t.close();
    }
}

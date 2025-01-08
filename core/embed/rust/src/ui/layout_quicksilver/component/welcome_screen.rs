use crate::ui::{
    component::{Component, Event, EventCtx, Never},
    display::font::Font,
    geometry::{Alignment, Alignment2D, Offset, Rect},
    shape,
    shape::Renderer,
};

use super::theme;

const TEXT_BOTTOM_MARGIN: i16 = 54;
const ICON_TOP_MARGIN: i16 = 48;
#[cfg(not(feature = "bootloader"))]
const MODEL_NAME_FONT: Font = Font::DEMIBOLD;

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

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        shape::ToifImage::new(
            self.area.top_center() + Offset::y(ICON_TOP_MARGIN),
            theme::ICON_LOGO.toif,
        )
        .with_align(Alignment2D::TOP_CENTER)
        .with_fg(theme::FG)
        .with_bg(theme::BG)
        .render(target);

        shape::Text::new(
            self.area.bottom_center() - Offset::y(TEXT_BOTTOM_MARGIN),
            model::FULL_NAME,
        )
        .with_align(Alignment::Center)
        .with_font(Font::NORMAL)
        .with_fg(theme::FG)
        .render(target);
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

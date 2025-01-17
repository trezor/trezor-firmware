use crate::ui::{
    component::{Component, Event, EventCtx, Never},
    geometry::{Alignment2D, Offset, Rect},
    shape,
    shape::Renderer,
};

use super::theme;
#[cfg(feature = "bootloader")]
use super::theme::bootloader::DEVICE_NAME;
#[cfg(feature = "bootloader")]
use crate::ui::display::toif::Toif;

const TEXT_BOTTOM_MARGIN: i16 = 24; // matching the homescreen label margin
const ICON_TOP_MARGIN: i16 = 48;
#[cfg(not(feature = "bootloader"))]
const MODEL_NAME_FONT: display::Font = display::Font::DEMIBOLD;
#[cfg(not(feature = "bootloader"))]
use crate::{
    trezorhal::model,
    ui::{display, geometry::Alignment},
};

pub struct WelcomeScreen {
    area: Rect,
    empty_lock: bool,
}

impl WelcomeScreen {
    pub fn new(empty_lock: bool) -> Self {
        Self {
            area: Rect::zero(),
            empty_lock,
        }
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
        let logo = if self.empty_lock {
            theme::ICON_LOGO_EMPTY
        } else {
            theme::ICON_LOGO
        };
        shape::ToifImage::new(
            self.area.top_center() + Offset::y(ICON_TOP_MARGIN),
            logo.toif,
        )
        .with_align(Alignment2D::TOP_CENTER)
        .with_fg(theme::FG)
        .with_bg(theme::BG)
        .render(target);

        #[cfg(not(feature = "bootloader"))]
        shape::Text::new(
            self.area.bottom_center() - Offset::y(TEXT_BOTTOM_MARGIN),
            model::FULL_NAME,
        )
        .with_align(Alignment::Center)
        .with_font(MODEL_NAME_FONT)
        .with_fg(theme::FG)
        .render(target);

        #[cfg(feature = "bootloader")]
        shape::ToifImage::new(
            self.area.bottom_center() - Offset::y(TEXT_BOTTOM_MARGIN),
            unwrap!(Toif::new(DEVICE_NAME)),
        )
        .with_align(Alignment2D::BOTTOM_CENTER)
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

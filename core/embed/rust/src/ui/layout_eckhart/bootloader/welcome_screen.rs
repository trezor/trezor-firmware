use crate::{
    strutil::TString,
    ui::{
        component::{Component, Event, EventCtx},
        geometry::{Offset, Point, Rect},
        shape::{self, Renderer},
    },
};

use super::{
    super::{constant::SCREEN, fonts, theme},
    BldActionBar, BldHeader,
};

#[cfg(feature = "power_manager")]
use super::BldHeaderMsg;

// TODO: adjust the origin
const TEXT_ORIGIN: Point = Point::new(24, 205);
const STRIDE: i16 = 38;

#[repr(u32)]
#[derive(Copy, Clone, ToPrimitive)]
pub enum WelcomeMsg {
    Cancel = 1,
    PairingMode = 2,
    Menu = 3,
}

/// Bootloader welcome screen
pub struct BldWelcomeScreen {
    header: Option<BldHeader<'static>>,
    action_bar: Option<BldActionBar>,
}

impl BldWelcomeScreen {
    pub fn new() -> Self {
        Self {
            header: Some(BldHeader::new(TString::empty()).with_menu_button()),
            action_bar: None,
        }
    }

    pub fn with_header(mut self, header: BldHeader<'static>) -> Self {
        self.header = Some(header);
        self
    }

    pub fn with_action_bar(mut self, action_bar: BldActionBar) -> Self {
        self.action_bar = Some(action_bar);
        self
    }
}

impl Component for BldWelcomeScreen {
    type Msg = WelcomeMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        let (header_area, rest) = SCREEN.split_top(theme::HEADER_HEIGHT);
        let (_rest, action_bar_area) = rest.split_bottom(theme::ACTION_BAR_HEIGHT);

        self.header.place(header_area);
        self.action_bar.place(action_bar_area);
        bounds
    }

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        #[cfg(all(feature = "ble", feature = "button"))]
        if let Event::Button(_) = _event {
            return Some(WelcomeMsg::PairingMode);
        }
        #[cfg(feature = "power_manager")]
        if let Some(BldHeaderMsg::Menu) = self.header.event(_ctx, _event) {
            return Some(WelcomeMsg::Menu);
        };
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.action_bar.render(target);
        #[cfg(feature = "power_manager")]
        self.header.render(target);

        let font = fonts::FONT_SATOSHI_REGULAR_38;
        shape::Text::new(TEXT_ORIGIN, "Get started", font)
            .with_fg(theme::GREY)
            .render(target);

        shape::Text::new(TEXT_ORIGIN + Offset::y(STRIDE), "with your Trezor", font)
            .with_fg(theme::GREY)
            .render(target);

        shape::Text::new(TEXT_ORIGIN + Offset::y(2 * STRIDE), "at", font)
            .with_fg(theme::GREY)
            .render(target);

        let at_width = font.text_width("at ");

        shape::Text::new(
            TEXT_ORIGIN + Offset::new(at_width, 2 * STRIDE),
            "trezor.io/start",
            font,
        )
        .with_fg(theme::GREY_EXTRA_LIGHT)
        .render(target);
    }
}

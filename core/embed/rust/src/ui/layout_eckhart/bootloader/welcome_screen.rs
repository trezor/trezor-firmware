use crate::{
    strutil::TString,
    trezorhal::ble,
    ui::{
        component::{Component, Event, EventCtx},
        geometry::{Alignment2D, Offset, Point, Rect},
        shape::{self, Renderer},
    },
};

use super::{
    super::{component::Button, constant::SCREEN, fonts, theme},
    BldActionBar, BldActionBarMsg, BldHeader,
};

#[cfg(feature = "power_manager")]
use super::BldHeaderMsg;

const TEXT_ORIGIN: Point = Point::new(24, 76);
const STRIDE: i16 = 46;

#[repr(u32)]
#[derive(Copy, Clone, ToPrimitive)]
pub enum WelcomeMsg {
    Cancel = 1,
    PairingMode = 2,
    Menu = 3,
}

/// Full-screen component for Bootloader welcome screen. This is the first
/// screen shown after the bootloader is started on empty device. The user can
/// initiate pairing. If the device is already paired, the screen shows a
/// message that Trezor is paired and Bootloader Menu is accessible.
pub struct BldWelcomeScreen {
    header: Option<BldHeader<'static>>,
    action_bar: BldActionBar,
    ble_paired: bool,
}

impl BldWelcomeScreen {
    pub fn new() -> Self {
        let ble_paired = ble::peer_count() > 0;
        let (header, button) = if ble_paired {
            (
                Some(BldHeader::new(TString::empty()).with_menu_button()),
                Button::with_text("More at trezor.io/start".into())
                    .styled(theme::bootloader::button_bld_initial_setup())
                    .initially_enabled(false),
            )
        } else {
            (
                None,
                Button::with_text("Tap to begin setup".into())
                    .styled(theme::bootloader::button_bld_initial_setup())
                    .with_gradient(theme::Gradient::DefaultGrey)
                    .initially_enabled(true),
            )
        };
        Self {
            header,
            action_bar: BldActionBar::new_single(button),
            ble_paired,
        }
    }
}

impl Component for BldWelcomeScreen {
    type Msg = WelcomeMsg;

    fn place(&mut self, _bounds: Rect) -> Rect {
        let (header_area, rest) = SCREEN.split_top(theme::HEADER_HEIGHT);
        let (_rest, action_bar_area) = rest.split_bottom(theme::ACTION_BAR_HEIGHT);

        self.header.place(header_area);
        self.action_bar.place(action_bar_area);
        SCREEN
    }

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        #[cfg(feature = "ble")]
        if let Some(BldActionBarMsg::Confirmed) = self.action_bar.event(_ctx, _event) {
            return Some(WelcomeMsg::PairingMode);
        }

        #[cfg(feature = "power_manager")]
        if let Some(BldHeaderMsg::Menu) = self.header.event(_ctx, _event) {
            return Some(WelcomeMsg::Menu);
        };
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        #[cfg(feature = "power_manager")]
        self.header.render(target);

        let font = fonts::FONT_SATOSHI_REGULAR_38;
        shape::Text::new(TEXT_ORIGIN, "Trezor", font)
            .with_fg(theme::GREY_LIGHT)
            .render(target);
        shape::Text::new(TEXT_ORIGIN + Offset::y(STRIDE), "Safe", font)
            .with_fg(theme::GREY_LIGHT)
            .render(target);
        shape::ToifImage::new(
            TEXT_ORIGIN + Offset::y(2 * STRIDE),
            theme::bootloader::ICON_SEVEN.toif,
        )
        .with_fg(theme::GREY)
        .with_align(Alignment2D::CENTER_LEFT)
        .render(target);

        // hint
        let icon_pos = Point::new(24, 398);
        let link_pos = icon_pos + Offset::x(theme::ICON_INFO.toif.width() + 12);
        let (hint_color, hint_text) = if self.ble_paired {
            (theme::GREEN_LIME, "Trezor is paired")
        } else {
            (theme::GREY, "trezor.io/start")
        };
        shape::ToifImage::new(icon_pos, theme::ICON_INFO.toif)
            .with_fg(hint_color)
            .with_align(Alignment2D::BOTTOM_LEFT)
            .render(target);
        shape::Text::new(link_pos, hint_text, fonts::FONT_SATOSHI_MEDIUM_26)
            .with_fg(hint_color)
            .render(target);

        self.action_bar.render(target);
    }
}

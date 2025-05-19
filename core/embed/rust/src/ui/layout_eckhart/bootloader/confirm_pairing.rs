use crate::{
    strutil::{format_i64, ShortString},
    ui::{
        component::{Component, Event, EventCtx},
        constant::SCREEN,
        event::BLEEvent,
        geometry::{Alignment, Rect},
        shape::{self, Renderer},
    },
};

use super::{
    super::{cshape::ScreenBorder, fonts, theme},
    BldActionBar, BldActionBarMsg, BldHeader,
};

#[derive(Copy, Clone, ToPrimitive)]
#[cfg_attr(feature = "debug", derive(ufmt::derive::uDebug))]
pub enum ConfirmPairingMsg {
    Cancel = 1,
    Confirm = 2,
}

pub struct ConfirmPairingScreen<'a> {
    header: Option<BldHeader<'a>>,
    action_bar: Option<BldActionBar>,
    screen_border: ScreenBorder,
    code_formatted: ShortString,
}

impl<'a> ConfirmPairingScreen<'a> {
    pub fn new(code: u32) -> Self {
        Self {
            header: None,
            action_bar: None,
            screen_border: ScreenBorder::new(theme::BLUE),
            code_formatted: Self::format_pairing_code(code),
        }
    }

    pub fn with_header(mut self, header: BldHeader<'a>) -> Self {
        self.header = Some(header);
        self
    }

    pub fn with_action_bar(mut self, action_bar: BldActionBar) -> Self {
        self.action_bar = Some(action_bar);
        self
    }

    /// Format the pairing code with zero-padding so that it always has a width
    /// of 6 digits.
    fn format_pairing_code(code: u32) -> ShortString {
        let mut buf = [0; 20];
        let code_str = unwrap!(format_i64(code as _, &mut buf));

        let width: usize = 6;
        let mut formatted_code = ShortString::new();
        // Add leading zeros
        for _ in 0..width.saturating_sub(code_str.len()) {
            unwrap!(formatted_code.push('0'));
        }
        // Add the actual digits
        unwrap!(formatted_code.push_str(code_str));
        formatted_code
    }
}

impl<'a> Component for ConfirmPairingScreen<'a> {
    type Msg = ConfirmPairingMsg;
    fn place(&mut self, bounds: Rect) -> Rect {
        let (header_area, rest) = bounds.split_top(theme::HEADER_HEIGHT);
        let (_rest, action_bar_area) = rest.split_bottom(theme::ACTION_BAR_HEIGHT);

        self.header.place(header_area);
        self.action_bar.place(action_bar_area);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Some(msg) = self.action_bar.event(ctx, event) {
            match msg {
                BldActionBarMsg::Cancelled => return Some(Self::Msg::Cancel),
                BldActionBarMsg::Confirmed => return Some(Self::Msg::Confirm),
            }
        }

        match event {
            Event::BLE(BLEEvent::PairingCanceled) => Some(Self::Msg::Cancel),
            Event::BLE(BLEEvent::Disconnected) => Some(Self::Msg::Cancel),
            Event::BLE(BLEEvent::Connected) => Some(Self::Msg::Cancel),
            _ => None,
        }
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.header.render(target);
        self.action_bar.render(target);
        self.screen_border.render(u8::MAX, target);

        // TODO: font size 72 is requested but it seems pricy for bootloader
        shape::Text::new(
            SCREEN.center(),
            &self.code_formatted,
            fonts::FONT_SATOSHI_REGULAR_38,
        )
        .with_fg(theme::GREY_EXTRA_LIGHT)
        .with_align(Alignment::Center)
        .render(target);
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for ConfirmPairingScreen<'_> {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("ConfirmPairing");
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_format_code() {
        let format_code = ConfirmPairingScreen::format_pairing_code;

        // Test normal cases with different digit counts
        assert_eq!(format_code(123).as_str(), "000123");
        assert_eq!(format_code(7).as_str(), "000007");
        assert_eq!(format_code(123456).as_str(), "123456");

        // Test boundary cases
        assert_eq!(format_code(0).as_str(), "000000");
        assert_eq!(format_code(999999).as_str(), "999999");
        assert_eq!(format_code(1000000).as_str(), "1000000"); // Exceeds 6 digits

        // Test with maximum u32 value
        assert_eq!(format_code(u32::MAX).as_str(), "4294967295");

        // Test with values having exactly 6 digits
        assert_eq!(format_code(100000).as_str(), "100000");
        assert_eq!(format_code(999999).as_str(), "999999");

        // Verify behavior with sequential values around boundaries
        assert_eq!(format_code(9999).as_str(), "009999");
        assert_eq!(format_code(10000).as_str(), "010000");
        assert_eq!(format_code(99999).as_str(), "099999");
        assert_eq!(format_code(100000).as_str(), "100000");
    }
}

use crate::{
    strutil::{format_pairing_code, ShortString},
    trezorhal::ble::PAIRING_CODE_LEN,
    ui::{
        component::{Component, Event, EventCtx, Label},
        constant::SCREEN,
        display::Font,
        event::BLEEvent,
        geometry::{Alignment, Offset, Point, Rect},
        shape::{self, Renderer},
    },
};

use super::{
    super::{component::Button, cshape::ScreenBorder, fonts, theme},
    BldActionBar, BldActionBarMsg, BldHeader,
};

#[derive(Copy, Clone, ToPrimitive)]
#[cfg_attr(feature = "debug", derive(ufmt::derive::uDebug))]
pub enum ConfirmPairingMsg {
    Cancel = 1,
    Confirm = 2,
}

pub struct ConfirmPairingScreen<'a> {
    header: BldHeader<'a>,
    instruction: Label<'static>,
    action_bar: BldActionBar,
    screen_border: Option<ScreenBorder>,
    code_formatted: ShortString,
}

impl<'a> ConfirmPairingScreen<'a> {
    pub fn new(code: u32) -> Self {
        let (left, right) = (
            Button::with_icon(theme::ICON_CROSS)
                .styled(theme::bootloader::button_bld_initial_setup()),
            Button::with_icon(theme::ICON_CHECKMARK)
                .styled(theme::bootloader::button_bld_initial_setup()),
        );

        Self {
            header: BldHeader::new("Bluetooth pairing".into()),
            instruction: Label::left_aligned("Pairing code match?".into(), theme::TEXT_NORMAL),
            action_bar: BldActionBar::new_double(left, right).with_divider(),
            screen_border: None,
            code_formatted: format_pairing_code(code, PAIRING_CODE_LEN),
        }
    }

    pub fn with_screen_border(mut self, screen_border: ScreenBorder) -> Self {
        self.screen_border = Some(screen_border);
        self
    }
}

impl<'a> Component for ConfirmPairingScreen<'a> {
    type Msg = ConfirmPairingMsg;
    fn place(&mut self, bounds: Rect) -> Rect {
        let (header_area, rest) = bounds.split_top(theme::HEADER_HEIGHT);
        let (content_area, action_bar_area) = rest.split_bottom(theme::ACTION_BAR_HEIGHT);
        let content_area = content_area.inset(theme::SIDE_INSETS);

        self.header.place(header_area);
        self.instruction.place(content_area);
        self.action_bar.place(action_bar_area);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.header.event(ctx, event);
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
        self.instruction.render(target);
        self.action_bar.render(target);
        if let Some(screen_border) = &self.screen_border {
            screen_border.render(u8::MAX, target);
        }

        const FONT_CODE: Font = fonts::FONT_SATOSHI_EXTRALIGHT_72_NUMS_ONLY;
        const BASE_POS: Point = SCREEN.center().ofs(Offset::y(FONT_CODE.height));

        shape::Text::new(BASE_POS, &self.code_formatted, FONT_CODE)
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

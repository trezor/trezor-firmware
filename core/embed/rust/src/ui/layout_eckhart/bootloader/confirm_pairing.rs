use crate::{
    strutil::format_i64,
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
    code: u32,
}

impl<'a> ConfirmPairingScreen<'a> {
    pub fn new(code: u32) -> Self {
        Self {
            header: None,
            action_bar: None,
            screen_border: ScreenBorder::new(theme::BLUE),
            code,
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

        let mut buf = [0; 20];
        let text = unwrap!(format_i64(self.code as _, &mut buf));
        // TODO: font size 72 is requested but it seems pricy for bootloader
        shape::Text::new(SCREEN.center(), text, fonts::FONT_SATOSHI_REGULAR_38)
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

use super::{
    super::{cshape::ScreenBorder, theme},
    BldActionBar, BldActionBarMsg,
};
use crate::{
    strutil::TString,
    ui::{
        component::{Component, Event, EventCtx, Label},
        event::BLEEvent,
        geometry::{Alignment, Rect},
        layout::simplified::ReturnToC,
        shape::Renderer,
    },
};

#[repr(u32)]
pub enum PairingMsg {
    Cancel,
    Pairing(u32),
}

impl ReturnToC for PairingMsg {
    fn return_to_c(self) -> u32 {
        match self {
            PairingMsg::Cancel => 1000000,
            PairingMsg::Pairing(code) => code,
        }
    }
}

pub struct PairingModeScreen {
    message: Label<'static>,
    name: Label<'static>,
    action_bar: Option<BldActionBar>,
    screen_border: ScreenBorder,
}

impl PairingModeScreen {
    pub fn new(message: TString<'static>, name: TString<'static>) -> Self {
        Self {
            message: Label::new(message, Alignment::Center, theme::TEXT_NORMAL),
            name: Label::new(name, Alignment::Center, theme::TEXT_NORMAL),
            action_bar: None,
            screen_border: ScreenBorder::new(theme::BLUE),
        }
    }

    pub fn with_action_bar(mut self, action_bar: BldActionBar) -> Self {
        self.action_bar = Some(action_bar);
        self
    }
}

impl Component for PairingModeScreen {
    type Msg = PairingMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        let (_header_area, rest) = bounds.split_top(theme::HEADER_HEIGHT);
        let (rest, action_bar_area) = rest.split_bottom(theme::ACTION_BAR_HEIGHT);
        let (content_area, name_area) = rest.inset(theme::SIDE_INSETS).split_top(70);
        self.message.place(content_area);
        self.name.place(name_area);
        self.action_bar.place(action_bar_area);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Some(BldActionBarMsg::Confirmed) = self.action_bar.event(ctx, event) {
            // Single mode ActionBar used to CancelPairing - so we map it to Msg::Cancel
            return Some(PairingMsg::Cancel);
        }

        if let Event::BLE(BLEEvent::PairingRequest(code)) = event {
            return Some(PairingMsg::Pairing(code));
        }
        if let Event::BLE(BLEEvent::PairingCanceled) = event {
            return Some(PairingMsg::Cancel);
        }
        if let Event::BLE(BLEEvent::Disconnected) = event {
            return Some(PairingMsg::Cancel);
        }

        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.message.render(target);
        self.name.render(target);
        self.action_bar.render(target);
        self.screen_border.render(u8::MAX, target);
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for PairingModeScreen {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("PairingMode");
        t.string("message", *self.message.text());
        t.string("name", *self.name.text());
    }
}

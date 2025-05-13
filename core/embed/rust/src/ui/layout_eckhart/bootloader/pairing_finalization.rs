use crate::{
    strutil::TString,
    ui::{
        component::{Component, Event, EventCtx, Label},
        event::BLEEvent,
        geometry::{Alignment, Rect},
        shape::Renderer,
    },
};

use super::{
    super::{cshape::ScreenBorder, theme},
    BldActionBar, BldActionBarMsg,
};

#[repr(u32)]
#[derive(Copy, Clone, ToPrimitive)]
pub enum PairingFinalizationMsg {
    Completed = 1,
    Cancel = 2,
    Failed = 3,
}

pub struct PairingFinalizationScreen {
    message: Label<'static>,
    action_bar: Option<BldActionBar>,
    screen_border: ScreenBorder,
}

impl PairingFinalizationScreen {
    pub fn new(message: TString<'static>) -> Self {
        Self {
            message: Label::new(message, Alignment::Center, theme::TEXT_NORMAL),
            action_bar: None,
            screen_border: ScreenBorder::new(theme::BLUE),
        }
    }

    pub fn with_action_bar(mut self, action_bar: BldActionBar) -> Self {
        self.action_bar = Some(action_bar);
        self
    }
}

impl Component for PairingFinalizationScreen {
    type Msg = PairingFinalizationMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        let (_header_area, rest) = bounds.split_top(theme::HEADER_HEIGHT);
        let (rest, action_bar_area) = rest.split_bottom(theme::ACTION_BAR_HEIGHT);
        let content_area = rest.inset(theme::SIDE_INSETS);
        self.action_bar.place(action_bar_area);
        self.message.place(content_area);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Some(BldActionBarMsg::Confirmed) = self.action_bar.event(ctx, event) {
            // Single mode ActionBar used to CancelPairing - so we map it to Msg::Cancel
            return Some(PairingFinalizationMsg::Cancel);
        }

        if let Event::BLE(BLEEvent::PairingCanceled) = event {
            return Some(PairingFinalizationMsg::Failed);
        }

        if let Event::BLE(BLEEvent::Disconnected) = event {
            return Some(PairingFinalizationMsg::Failed);
        }

        if let Event::BLE(BLEEvent::PairingCompleted) = event {
            return Some(PairingFinalizationMsg::Completed);
        }

        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.action_bar.render(target);
        self.message.render(target);
        self.screen_border.render(u8::MAX, target);
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for PairingFinalizationScreen {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("ParingFinalization");
        t.string("message", *self.message.text());
    }
}

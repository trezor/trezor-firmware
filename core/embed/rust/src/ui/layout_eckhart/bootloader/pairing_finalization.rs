use crate::ui::{
    component::{Component, Event, EventCtx, Label},
    event::BLEEvent,
    geometry::Rect,
    shape::Renderer,
};

use super::{
    super::{component::Button, cshape::ScreenBorder, theme},
    BldActionBar, BldActionBarMsg, BldHeader,
};

#[repr(u32)]
#[derive(Copy, Clone, ToPrimitive)]
pub enum PairingFinalizationMsg {
    Completed = 1,
    Cancel = 2,
    Failed = 3,
}

pub struct PairingFinalizationScreen {
    header: BldHeader<'static>,
    message: Label<'static>,
    action_bar: BldActionBar,
    screen_border: Option<ScreenBorder>,
}

impl PairingFinalizationScreen {
    pub fn new() -> Self {
        let btn = Button::with_text("Cancel".into()).styled(theme::button_default());
        Self {
            header: BldHeader::new("Bluetooth pairing".into()),
            message: Label::left_aligned(
                "Waiting for confirmation on host device.".into(),
                theme::TEXT_NORMAL,
            ),
            action_bar: BldActionBar::new_single(btn),
            screen_border: None,
        }
    }

    pub fn with_screen_border(mut self, screen_border: ScreenBorder) -> Self {
        self.screen_border = Some(screen_border);
        self
    }
}

impl Component for PairingFinalizationScreen {
    type Msg = PairingFinalizationMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        let (header_area, rest) = bounds.split_top(theme::HEADER_HEIGHT);
        let (rest, action_bar_area) = rest.split_bottom(theme::ACTION_BAR_HEIGHT);
        let content_area = rest.inset(theme::SIDE_INSETS);
        self.header.place(header_area);
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
        self.header.render(target);
        self.action_bar.render(target);
        self.message.render(target);
        if let Some(screen_border) = &self.screen_border {
            screen_border.render(u8::MAX, target);
        }
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for PairingFinalizationScreen {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("ParingFinalization");
        t.string("message", *self.message.text());
    }
}

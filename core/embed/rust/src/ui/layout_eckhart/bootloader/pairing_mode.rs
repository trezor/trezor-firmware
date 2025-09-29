use super::{
    super::{cshape::ScreenBorder, theme},
    BldHeader, BldHeaderMsg,
};
use crate::{
    strutil::TString,
    ui::{
        component::{text::TextStyle, Component, Event, EventCtx, Label},
        event::BLEEvent,
        geometry::{Insets, Rect},
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
    header: BldHeader<'static>,
    name: Label<'static>,
    message: Label<'static>,
    footer: Label<'static>,
    screen_border: Option<ScreenBorder>,
}

impl PairingModeScreen {
    const TEXT_NORMAL_GREEN_LIME: TextStyle = TextStyle {
        text_color: theme::GREEN_LIME,
        ..theme::TEXT_NORMAL
    };

    pub fn new(name: TString<'static>) -> Self {
        Self {
            header: BldHeader::new("Pair new device".into()).with_close_button(),
            name: Label::left_aligned(name, Self::TEXT_NORMAL_GREEN_LIME),
            message: Label::left_aligned("is your Trezor's name.".into(), theme::TEXT_NORMAL),
            footer: Label::centered("Continue on host".into(), theme::TEXT_SMALL_GREY)
                .vertically_centered(),
            screen_border: None,
        }
    }

    pub fn with_screen_border(mut self, screen_border: ScreenBorder) -> Self {
        self.screen_border = Some(screen_border);
        self
    }
}

impl Component for PairingModeScreen {
    type Msg = PairingMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        let (header_area, rest) = bounds.split_top(theme::HEADER_HEIGHT);
        let (rest, action_bar_area) = rest.split_bottom(theme::ACTION_BAR_HEIGHT);
        let rest = rest.inset(theme::SIDE_INSETS);
        let (name_area, content_area) = rest.split_top(self.name.text_height(rest.width()));
        let content_area = content_area.inset(Insets::top(4));
        self.header.place(header_area);
        self.name.place(name_area);
        self.message.place(content_area);
        self.footer.place(action_bar_area);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Some(BldHeaderMsg::Cancelled) = self.header.event(ctx, event) {
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
        if let Event::BLE(BLEEvent::PairingNotNeeded) = event {
            return Some(PairingMsg::Cancel);
        }

        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.header.render(target);
        self.name.render(target);
        self.message.render(target);
        self.footer.render(target);
        if let Some(screen_border) = &self.screen_border {
            screen_border.render(u8::MAX, target);
        }
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for PairingModeScreen {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("PairingMode");
        t.string("name", *self.name.text());
        t.string("message", *self.message.text());
    }
}

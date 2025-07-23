use crate::{
    strutil::TString,
    ui::{
        component::{Component, Event, EventCtx, Pad},
        display::{Color, Font},
        event::BLEEvent,
        geometry::{Alignment, Offset, Rect},
        layout::simplified::ReturnToC,
        shape::{self, Renderer},
    },
};

use super::{Button, ButtonMsg};

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

pub struct PairingMode {
    fg: Color,
    bg: Pad,
    message: TString<'static>,
    font: Font,
    button: Button,
}

impl PairingMode {
    pub fn new(
        message: TString<'static>,
        font: Font,
        fg: Color,
        bg: Color,
        button: Button,
    ) -> Self {
        let mut instance = Self {
            fg,
            bg: Pad::with_background(bg),
            message,
            font,
            button,
        };

        instance.bg.clear();
        instance
    }
}

impl Component for PairingMode {
    type Msg = PairingMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.bg.place(bounds);
        self.button.place(bounds.split_bottom(60).1);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Some(ButtonMsg::Clicked) = self.button.event(ctx, event) {
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
        self.bg.render(target);
        self.button.render(target);

        self.message.map(|t| {
            shape::Text::new(
                self.bg.area.center() + Offset::y(self.font.text_height() / 2),
                t,
                self.font,
            )
            .with_fg(self.fg)
            .with_align(Alignment::Center)
            .render(target);
        });
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for PairingMode {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("PairingMode");
        t.string("message", self.message);
    }
}

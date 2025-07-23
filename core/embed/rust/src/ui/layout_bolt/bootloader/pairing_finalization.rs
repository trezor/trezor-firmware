use crate::{
    strutil::TString,
    ui::{
        component::{Component, Event, EventCtx, Pad},
        display::{Color, Font},
        event::BLEEvent,
        geometry::{Alignment, Offset, Point, Rect},
        shape::{self, Renderer},
    },
};

use super::super::{
    component::{Button, ButtonMsg},
    constant::WIDTH,
    theme::bootloader::{BUTTON_AREA_START, BUTTON_HEIGHT, CONTENT_PADDING},
};

#[repr(u32)]
#[derive(Copy, Clone, ToPrimitive)]
pub enum PairingFinalizationMsg {
    Completed = 1,
    Cancel = 2,
    Failed = 3,
}

pub struct PairingFinalization {
    fg: Color,
    bg: Pad,
    message: TString<'static>,
    font: Font,
    button: Button,
}

impl PairingFinalization {
    pub fn new<T>(message: T, font: Font, fg: Color, bg: Color, button: Button) -> Self
    where
        T: Into<TString<'static>>,
    {
        let mut instance = Self {
            fg,
            bg: Pad::with_background(bg),
            message: message.into(),
            font,
            button,
        };

        instance.bg.clear();
        instance
    }
}

impl Component for PairingFinalization {
    type Msg = PairingFinalizationMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.bg.place(bounds);
        self.button.place(Rect::new(
            Point::new(CONTENT_PADDING, BUTTON_AREA_START),
            Point::new(WIDTH - CONTENT_PADDING, BUTTON_AREA_START + BUTTON_HEIGHT),
        ));

        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Some(ButtonMsg::Clicked) = self.button.event(ctx, event) {
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
impl crate::trace::Trace for PairingFinalization {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("ParingFinalization");
        t.string("message", self.message);
    }
}

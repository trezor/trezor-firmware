use crate::{
    strutil::TString,
    ui::{
        component::{Component, Event, EventCtx, Pad},
        display::{Color, Font},
        geometry::{Alignment, Offset, Rect},
        shape::{self, Renderer},
    },
};

use super::super::{
    component::{ButtonController, ButtonControllerMsg, ButtonLayout, ButtonPos},
    theme::{BUTTON_HEIGHT, TITLE_AREA_HEIGHT},
};

#[repr(u32)]
#[derive(Copy, Clone, ToPrimitive)]
pub enum ConnectMsg {
    Cancel = 1,
    PairingMode = 2,
}

pub struct Connect {
    fg: Color,
    bg: Pad,
    message: TString<'static>,
    font: Font,
    buttons: ButtonController,
}

impl Connect {
    pub fn new<T>(message: T, font: Font, fg: Color, bg: Color) -> Self
    where
        T: Into<TString<'static>>,
    {
        let mut instance = Self {
            fg,
            bg: Pad::with_background(bg),
            message: message.into(),
            font,
            buttons: ButtonController::new(ButtonLayout::none_none_text("Cancel".into())),
        };

        instance.bg.clear();
        instance
    }
}

impl Component for Connect {
    type Msg = ConnectMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.bg.place(bounds);

        // Title on top, buttons on bottom, text in between
        let (_, text_and_buttons_area) = bounds.split_top(TITLE_AREA_HEIGHT);
        let (_, buttons_area) = text_and_buttons_area.split_bottom(BUTTON_HEIGHT);

        self.buttons.place(buttons_area);

        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Some(ButtonControllerMsg::Triggered(ButtonPos::Right, false)) =
            self.buttons.event(ctx, event)
        {
            return Some(ConnectMsg::Cancel);
        }

        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.bg.render(target);
        self.buttons.render(target);

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
impl crate::trace::Trace for Connect {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Connect");
        t.string("message", self.message);
    }
}

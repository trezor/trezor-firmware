use crate::{
    strutil::TString,
    ui::{
        component::{Component, Event, EventCtx, Pad},
        display::{Color, Font},
        geometry::{Alignment, Offset, Rect},
        layout_bolt::{
            component::{Button, ButtonMsg},
            theme::bootloader::button_bld,
        },
        shape::{self, Renderer},
    },
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
    button: Button,
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
            button: Button::with_text("Cancel".into()).styled(button_bld()),
        };

        instance.bg.clear();
        instance
    }
}

impl Component for Connect {
    type Msg = ConnectMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.bg.place(bounds);
        self.button.place(bounds.split_bottom(60).1);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Some(msg) = self.button.event(ctx, event) {
            match msg {
                ButtonMsg::Clicked => return Some(ConnectMsg::Cancel),
                _ => {}
            }
        }

        #[cfg(all(feature = "ble", feature = "button"))]
        if let Event::Button(_) = event {
            return Some(ConnectMsg::PairingMode);
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
impl crate::trace::Trace for Connect {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Connect");
        t.string("message", self.message);
    }
}

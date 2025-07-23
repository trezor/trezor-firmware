use super::{
    super::{
        constant::WIDTH,
        theme::bootloader::{BUTTON_AREA_START, BUTTON_HEIGHT, CONTENT_PADDING, TITLE_AREA},
    },
    Button,
    ButtonMsg::Clicked,
};
use crate::{
    strutil::format_i64,
    ui::{
        component::{Child, Component, Event, EventCtx, Label, Pad},
        constant,
        display::Color,
        event::BLEEvent,
        geometry::{Offset, Point, Rect},
        shape,
        shape::Renderer,
    },
};

use super::{super::fonts, theme::WHITE};

const ICON_TOP: i16 = 17;
const CONTENT_START: i16 = 72;

const CONTENT_AREA: Rect = Rect::new(
    Point::new(CONTENT_PADDING, CONTENT_START),
    Point::new(WIDTH - CONTENT_PADDING, BUTTON_AREA_START - CONTENT_PADDING),
);

#[derive(Copy, Clone, ToPrimitive)]
#[cfg_attr(feature = "debug", derive(ufmt::derive::uDebug))]
pub enum ConfirmPairingMsg {
    Cancel = 1,
    Confirm = 2,
}

pub struct ConfirmPairing<'a> {
    bg: Pad,
    content_pad: Pad,
    bg_color: Color,
    title: Label<'a>,
    code: u32,
    left_button: Child<Button>,
    right_button: Child<Button>,
}

impl<'a> ConfirmPairing<'a> {
    pub fn new(
        bg_color: Color,
        left_button: Button,
        right_button: Button,
        title: Label<'a>,
        code: u32,
    ) -> Self {
        Self {
            bg: Pad::with_background(bg_color).with_clear(),
            content_pad: Pad::with_background(bg_color),
            bg_color,
            title,
            left_button: Child::new(left_button),
            right_button: Child::new(right_button),
            code,
        }
    }
}

impl Component for ConfirmPairing<'_> {
    type Msg = ConfirmPairingMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.bg.place(constant::screen());
        self.content_pad.place(Rect::new(
            Point::zero(),
            Point::new(WIDTH, BUTTON_AREA_START),
        ));

        self.title.place(TITLE_AREA);

        let button_size = Offset::new((WIDTH - 3 * CONTENT_PADDING) / 2, BUTTON_HEIGHT);
        self.left_button.place(Rect::from_top_left_and_size(
            Point::new(CONTENT_PADDING, BUTTON_AREA_START),
            button_size,
        ));
        self.right_button.place(Rect::from_top_left_and_size(
            Point::new(2 * CONTENT_PADDING + button_size.x, BUTTON_AREA_START),
            button_size,
        ));

        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Some(Clicked) = self.left_button.event(ctx, event) {
            return Some(Self::Msg::Cancel);
        };
        if let Some(Clicked) = self.right_button.event(ctx, event) {
            return Some(Self::Msg::Confirm);
        };
        match event {
            Event::BLE(BLEEvent::PairingCanceled) => Some(Self::Msg::Cancel),
            Event::BLE(BLEEvent::Disconnected) => Some(Self::Msg::Cancel),
            Event::BLE(BLEEvent::Connected) => Some(Self::Msg::Cancel),
            _ => None,
        }
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.bg.render(target);
        self.content_pad.render(target);

        self.left_button.render(target);
        self.right_button.render(target);
        self.title.render(target);

        let mut buf = [0; 20];
        let text = unwrap!(format_i64(self.code as _, &mut buf));

        shape::Text::new(CONTENT_AREA.left_center(), text, fonts::FONT_BOLD_UPPER)
            .with_fg(WHITE)
            .render(target);
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for ConfirmPairing<'_> {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("ConfirmPairing");
    }
}

use crate::ui::{
    component::{text::paragraphs::Paragraphs, Child, Component, Event, EventCtx, Pad},
    constant::screen,
    display,
    display::Color,
    geometry::{Offset, Point, Rect},
    model_tt::{
        component::{Button, ButtonMsg::Clicked},
        constant::{HEIGHT, WIDTH},
        theme::WHITE,
    },
};

use super::ReturnToC;

#[derive(Copy, Clone)]
pub enum ConfirmMsg {
    Cancel = 1,
    Confirm = 2,
}

impl ReturnToC for ConfirmMsg {
    fn return_to_c(self) -> u32 {
        self as u32
    }
}

pub struct Confirm {
    bg: Pad,
    bg_color: Color,
    icon: Option<&'static [u8]>,
    message: Child<Paragraphs<&'static str>>,
    left: Child<Button<&'static str>>,
    right: Child<Button<&'static str>>,
    confirm_left: bool,
}

impl Confirm {
    pub fn new(
        bg_color: Color,
        icon: Option<&'static [u8]>,
        message: Paragraphs<&'static str>,
        left: Button<&'static str>,
        right: Button<&'static str>,
        confirm_left: bool,
    ) -> Self {
        let mut instance = Self {
            bg: Pad::with_background(bg_color),
            bg_color,
            icon,
            message: Child::new(message),
            left: Child::new(left),
            right: Child::new(right),
            confirm_left,
        };
        instance.bg.clear();
        instance
    }
}

impl Component for Confirm {
    type Msg = ConfirmMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.bg
            .place(Rect::new(Point::new(0, 0), Point::new(WIDTH, HEIGHT)));
        self.message.place(Rect::new(
            Point::new(15, 59),
            Point::new(WIDTH - 15, HEIGHT - 64),
        ));

        let button_size = Offset::new(102, 48);
        self.left.place(Rect::from_top_left_and_size(
            Point::new(15, 176),
            button_size,
        ));
        self.right.place(Rect::from_top_left_and_size(
            Point::new(123, 176),
            button_size,
        ));
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Some(Clicked) = self.left.event(ctx, event) {
            return if self.confirm_left {
                Some(Self::Msg::Confirm)
            } else {
                Some(Self::Msg::Cancel)
            };
        };
        if let Some(Clicked) = self.right.event(ctx, event) {
            return if self.confirm_left {
                Some(Self::Msg::Cancel)
            } else {
                Some(Self::Msg::Confirm)
            };
        };
        None
    }

    fn paint(&mut self) {
        self.bg.paint();

        if let Some(icon) = self.icon {
            display::icon(
                Point::new(screen().center().x, 45),
                icon,
                WHITE,
                self.bg_color,
            );
        }

        self.message.paint();
        self.left.paint();
        self.right.paint();
    }

    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        self.left.bounds(sink);
        self.right.bounds(sink);
    }
}

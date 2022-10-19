use crate::ui::{
    component::{
        text::paragraphs::{ParagraphVecShort, Paragraphs},
        Child, Component, Event, EventCtx, Pad,
    },
    constant::screen,
    display::{Color, Icon},
    geometry::{Point, Rect, CENTER},
    model_tr::{
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
    icon: Option<Icon>,
    message: Child<Paragraphs<ParagraphVecShort<&'static str>>>,
    left: Child<Button<&'static str>>,
    right: Child<Button<&'static str>>,
    confirm_left: bool,
}

impl Confirm {
    pub fn new(
        bg_color: Color,
        icon: Option<Icon>,
        message: Paragraphs<ParagraphVecShort<&'static str>>,
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
        self.message
            .place(Rect::new(Point::new(10, 0), Point::new(118, 50)));

        let button_area = bounds.split_bottom(12).1;
        self.left.place(button_area);
        self.right.place(button_area);

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
            icon.draw(
                Point::new(screen().center().x, 45),
                CENTER,
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

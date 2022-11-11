use crate::ui::{
    component::{
        text::paragraphs::{ParagraphVecShort, Paragraphs},
        Child, Component, Event, EventCtx, Pad,
    },
    constant::screen,
    display,
    display::{Color, Font},
    geometry::{Point, Rect},
    model_tr::{
        bootloader::theme::WHITE,
        component::{ButtonController, ButtonControllerMsg, ButtonLayout, ButtonPos},
        constant::{HEIGHT, WIDTH},
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
    label: &'static str,
    message: Child<Paragraphs<ParagraphVecShort<&'static str>>>,
    buttons: ButtonController<&'static str>,
    confirm_left: bool,
}

impl Confirm {
    pub fn new(
        bg_color: Color,
        icon: Option<&'static [u8]>,
        label: &'static str,
        message: Paragraphs<ParagraphVecShort<&'static str>>,
        text: &'static str,
        confirm_left: bool,
    ) -> Self {
        let mut instance = Self {
            bg: Pad::with_background(bg_color),
            bg_color,
            icon,
            label,
            message: Child::new(message),
            buttons: ButtonController::new(ButtonLayout::cancel_and_text(text)),
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
            .place(Rect::new(Point::new(0, 10), Point::new(128, 54)));

        let button_area = bounds.split_bottom(12).1;
        self.buttons.place(button_area);

        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        match self.buttons.event(ctx, event) {
            Some(ButtonControllerMsg::Triggered(ButtonPos::Left)) => Some(ConfirmMsg::Cancel),
            Some(ButtonControllerMsg::Triggered(ButtonPos::Right)) => Some(ConfirmMsg::Confirm),
            _ => None,
        }
        // if let Some(Clicked) = self.left.event(ctx, event) {
        //     return if self.confirm_left {
        //         Some(Self::Msg::Confirm)
        //     } else {
        //         Some(Self::Msg::Cancel)
        //     };
        // };
        // if let Some(Clicked) = self.right.event(ctx, event) {
        //     return if self.confirm_left {
        //         Some(Self::Msg::Cancel)
        //     } else {
        //         Some(Self::Msg::Confirm)
        //     };
        // };
        //None
    }

    fn paint(&mut self) {
        self.bg.paint();

        display::text_top_left(Point::zero(), self.label, Font::BOLD, WHITE, self.bg_color);

        if let Some(icon) = self.icon {
            display::icon(
                Point::new(screen().center().x, 45),
                icon,
                WHITE,
                self.bg_color,
            );
        }

        self.message.paint();
        self.buttons.paint();
    }

    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        self.buttons.bounds(sink);
    }
}

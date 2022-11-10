use crate::ui::{
    component::{
        text::paragraphs::{ParagraphVecShort, Paragraphs},
        Child, Component, ComponentExt, Event, EventCtx, Pad,
    },
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
pub enum ConfirmSeedMsg {
    Cancel = 1,
    Confirm = 2,
}

impl ReturnToC for ConfirmSeedMsg {
    fn return_to_c(self) -> u32 {
        self as u32
    }
}

pub struct ConfirmSeed<'a> {
    bg: Pad,
    bg_color: Color,
    label: &'static str,
    message: Child<Paragraphs<ParagraphVecShort<&'a str>>>,
    message2: Child<Paragraphs<ParagraphVecShort<&'a str>>>,
    buttons: ButtonController,
    buttons2: ButtonController,
    confirm_left: bool,
    page: i16,
}

impl<'a> ConfirmSeed<'a> {
    pub fn new(
        bg_color: Color,
        label: &'static str,
        message: Paragraphs<ParagraphVecShort<&'a str>>,
        message2: Paragraphs<ParagraphVecShort<&'a str>>,
        text: &'static str,
        confirm_left: bool,
    ) -> Self {
        let mut instance = Self {
            bg: Pad::with_background(bg_color),
            bg_color,
            label,
            message: Child::new(message),
            message2: Child::new(message2),
            buttons: ButtonController::new(ButtonLayout::cancel_none_arrow()),
            buttons2: ButtonController::new(ButtonLayout::up_and_text(text.into())),
            confirm_left,
            page: 0,
        };
        instance.bg.clear();
        instance
    }
}

impl<'a> Component for ConfirmSeed<'a> {
    type Msg = ConfirmSeedMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.bg
            .place(Rect::new(Point::new(0, 0), Point::new(WIDTH, HEIGHT)));
        self.message
            .place(Rect::new(Point::new(0, 9), Point::new(128, 54)));
        self.message2
            .place(Rect::new(Point::new(0, 9), Point::new(128, 54)));

        let button_area = bounds.split_bottom(12).1;
        self.buttons.place(button_area);
        self.buttons2.place(button_area);

        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if self.page == 0 {
            match self.buttons.event(ctx, event) {
                Some(ButtonControllerMsg::Triggered(ButtonPos::Left)) => {
                    Some(ConfirmSeedMsg::Cancel)
                }
                Some(ButtonControllerMsg::Triggered(ButtonPos::Right)) => {
                    self.page = 1;
                    ctx.request_paint();
                    self.message2.request_complete_repaint(ctx);
                    self.buttons2.request_complete_repaint(ctx);
                    self.bg.clear();
                    None
                }
                _ => None,
            }
        } else {
            match self.buttons2.event(ctx, event) {
                Some(ButtonControllerMsg::Triggered(ButtonPos::Left)) => {
                    self.page = 0;
                    ctx.request_paint();
                    self.message.request_complete_repaint(ctx);
                    self.buttons.request_complete_repaint(ctx);
                    self.bg.clear();
                    None
                }
                Some(ButtonControllerMsg::Triggered(ButtonPos::Right)) => {
                    Some(ConfirmSeedMsg::Confirm)
                }
                _ => None,
            }
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

        if self.page == 0 {
            self.message.paint();
            self.buttons.paint();
        } else {
            self.message2.paint();
            self.buttons2.paint();
        }
    }

    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        self.buttons.bounds(sink);
    }
}

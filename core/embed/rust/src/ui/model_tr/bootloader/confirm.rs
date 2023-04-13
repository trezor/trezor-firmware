use crate::ui::{
    component::{Child, Component, ComponentExt, Event, EventCtx, Label, Pad},
    display,
    display::{Color, Font},
    geometry::{Point, Rect},
    model_tr::{
        bootloader::theme::WHITE,
        component::{ButtonController, ButtonControllerMsg, ButtonLayout, ButtonPos},
        constant::WIDTH,
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

pub struct Confirm<'a> {
    bg: Pad,
    bg_color: Color,
    label: &'static str,
    message: Child<Label<&'a str>>,
    buttons: ButtonController<&'static str>,
    buttons_info: ButtonController<&'static str>,
    alert: Option<Label<&'a str>>,
    info: Option<Label<&'a str>>,
    info_shown: bool,
}

impl<'a> Confirm<'a> {
    pub fn new(
        bg_color: Color,
        label: &'static str,
        message: Label<&'a str>,
        alert: Option<Label<&'a str>>,
        info: Option<Label<&'a str>>,
        text: &'static str,
    ) -> Self {
        let controller = if info.is_some() {
            ButtonController::new(ButtonLayout::cancel_armed_text("INSTALL", " i "))
        } else {
            ButtonController::new(ButtonLayout::cancel_none_text(text))
        };
        Self {
            bg: Pad::with_background(bg_color).with_clear(),
            bg_color,
            label,
            message: Child::new(message),
            alert,
            info,
            buttons: controller,
            buttons_info: ButtonController::new(ButtonLayout::arrow_none_none()),
            info_shown: false,
        }
    }
}

impl<'a> Component for Confirm<'a> {
    type Msg = ConfirmMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.bg.place(bounds);

        let (message_area, alert_area) = if self.alert.is_some() {
            (
                Rect::new(Point::new(0, 12), Point::new(WIDTH, 39)),
                Rect::new(Point::new(0, 39), Point::new(WIDTH, 54)),
            )
        } else {
            (
                Rect::new(Point::new(0, 12), Point::new(WIDTH, 54)),
                Rect::zero(),
            )
        };

        self.message.place(message_area);
        self.alert.place(alert_area);
        self.info
            .place(Rect::new(Point::new(0, 12), Point::new(WIDTH, 54)));

        let button_area = bounds.split_bottom(12).1;
        self.buttons.place(button_area);
        self.buttons_info.place(button_area);

        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if self.info_shown {
            if let Some(ButtonControllerMsg::Triggered(ButtonPos::Left)) =
                self.buttons.event(ctx, event)
            {
                self.info_shown = false;
                self.message.request_complete_repaint(ctx);
                self.buttons.request_complete_repaint(ctx);
                self.bg.clear();
                self.request_complete_repaint(ctx);
            };
            None
        } else if self.info.is_some() {
            match self.buttons.event(ctx, event) {
                Some(ButtonControllerMsg::Triggered(ButtonPos::Left)) => Some(ConfirmMsg::Cancel),
                Some(ButtonControllerMsg::Triggered(ButtonPos::Middle)) => {
                    Some(ConfirmMsg::Confirm)
                }
                Some(ButtonControllerMsg::Triggered(ButtonPos::Right)) => {
                    self.info_shown = true;
                    self.bg.clear();
                    self.info.request_complete_repaint(ctx);
                    self.buttons_info.request_complete_repaint(ctx);
                    self.request_complete_repaint(ctx);
                    None
                }
                _ => None,
            }
        } else {
            match self.buttons.event(ctx, event) {
                Some(ButtonControllerMsg::Triggered(ButtonPos::Left)) => Some(ConfirmMsg::Cancel),
                Some(ButtonControllerMsg::Triggered(ButtonPos::Right)) => Some(ConfirmMsg::Confirm),
                _ => None,
            }
        }
    }

    fn paint(&mut self) {
        self.bg.paint();

        display::text_top_left(Point::zero(), self.label, Font::BOLD, WHITE, self.bg_color);

        if self.info_shown {
            self.info.paint();
            self.buttons_info.paint();
        } else {
            self.message.paint();
            self.alert.paint();
            self.buttons.paint();
        }
    }

    #[cfg(feature = "ui_bounds")]
    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        self.buttons.bounds(sink);
    }
}

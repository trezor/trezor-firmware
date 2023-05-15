use crate::ui::{
    component::{Child, Component, ComponentExt, Event, EventCtx, Label, Pad},
    constant::HEIGHT,
    display,
    display::{Color, Font, Icon},
    geometry::{Point, Rect},
    model_tr::{
        bootloader::theme::{ICON_INFO, ICON_INFO_INVERTED, WHITE},
        component::{ButtonController, ButtonControllerMsg, ButtonLayout, ButtonPos},
        constant::WIDTH,
        theme::{BUTTON_HEIGHT, TITLE_AREA_HEIGHT},
    },
};

use super::ReturnToC;

const ALERT_AREA_START: i16 = 39;

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
    info_title: Option<&'static str>,
    info_text: Option<Label<&'a str>>,
    info_shown: bool,
}

impl<'a> Confirm<'a> {
    pub fn new(
        bg_color: Color,
        label: &'static str,
        message: Label<&'a str>,
        alert: Option<Label<&'a str>>,
        info: Option<(&'static str, Label<&'a str>)>,
        text: &'static str,
    ) -> Self {
        let controller = if info.is_some() {
            ButtonController::new(ButtonLayout::cancel_armed_icon(
                "INSTALL",
                (Icon::new(ICON_INFO), Some(Icon::new(ICON_INFO_INVERTED))),
            ))
        } else {
            ButtonController::new(ButtonLayout::cancel_none_text(text))
        };
        let mut instance = Self {
            bg: Pad::with_background(bg_color).with_clear(),
            bg_color,
            label,
            message: Child::new(message),
            alert,
            info_title: None,
            info_text: None,
            buttons: controller,
            buttons_info: ButtonController::new(ButtonLayout::arrow_none_none()),
            info_shown: false,
        };

        if let Some(info) = info {
            instance.info_title = Some(info.0);
            instance.info_text = Some(info.1);
        };

        instance
    }
}

impl<'a> Component for Confirm<'a> {
    type Msg = ConfirmMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.bg.place(bounds);

        let (message_area, alert_area) = if self.alert.is_some() {
            (
                Rect::new(
                    Point::new(0, TITLE_AREA_HEIGHT),
                    Point::new(WIDTH, ALERT_AREA_START),
                ),
                Rect::new(
                    Point::new(0, ALERT_AREA_START),
                    Point::new(WIDTH, HEIGHT - BUTTON_HEIGHT),
                ),
            )
        } else {
            (
                Rect::new(
                    Point::new(0, TITLE_AREA_HEIGHT),
                    Point::new(WIDTH, HEIGHT - BUTTON_HEIGHT),
                ),
                Rect::zero(),
            )
        };

        self.message.place(message_area);
        self.alert.place(alert_area);
        self.info_text.place(Rect::new(
            Point::new(0, TITLE_AREA_HEIGHT),
            Point::new(WIDTH, HEIGHT - BUTTON_HEIGHT),
        ));

        let button_area = bounds.split_bottom(BUTTON_HEIGHT).1;
        self.buttons.place(button_area);
        self.buttons_info.place(button_area);

        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if self.info_shown {
            if let Some(ButtonControllerMsg::Triggered(ButtonPos::Left)) =
                self.buttons_info.event(ctx, event)
            {
                self.info_shown = false;
                self.message.request_complete_repaint(ctx);
                self.buttons.request_complete_repaint(ctx);
                self.bg.clear();
                self.request_complete_repaint(ctx);
            };
            None
        } else if self.info_text.is_some() {
            match self.buttons.event(ctx, event) {
                Some(ButtonControllerMsg::Triggered(ButtonPos::Left)) => Some(ConfirmMsg::Cancel),
                Some(ButtonControllerMsg::Triggered(ButtonPos::Middle)) => {
                    Some(ConfirmMsg::Confirm)
                }
                Some(ButtonControllerMsg::Triggered(ButtonPos::Right)) => {
                    self.info_shown = true;
                    self.bg.clear();
                    self.info_text.request_complete_repaint(ctx);
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

        if self.info_shown {
            display::text_top_left(
                Point::zero(),
                unwrap!(self.info_title),
                Font::BOLD,
                WHITE,
                self.bg_color,
            );
            self.info_text.paint();
            self.buttons_info.paint();
        } else {
            display::text_top_left(Point::zero(), self.label, Font::BOLD, WHITE, self.bg_color);
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

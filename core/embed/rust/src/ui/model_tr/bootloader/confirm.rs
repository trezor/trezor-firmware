use crate::ui::{
    component::{Child, Component, ComponentExt, Event, EventCtx, Label, Pad},
    display::{self, Color, Font},
    geometry::{Point, Rect},
};

use super::{
    super::{
        component::{ButtonController, ButtonControllerMsg, ButtonLayout, ButtonPos},
        theme::{BUTTON_HEIGHT, TITLE_AREA_HEIGHT},
    },
    theme::WHITE,
    ReturnToC,
};

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
    title: &'static str,
    message: Child<Label<&'a str>>,
    alert: Option<Label<&'a str>>,
    info_title: Option<&'static str>,
    info_text: Option<Label<&'a str>>,
    button_text: &'static str,
    buttons: ButtonController<&'static str>,
    /// Whether we are on the info screen (optional extra screen)
    showing_info_screen: bool,
}

impl<'a> Confirm<'a> {
    pub fn new(
        bg_color: Color,
        title: &'static str,
        message: Label<&'a str>,
        alert: Option<Label<&'a str>>,
        button_text: &'static str,
    ) -> Self {
        let btn_layout = Self::get_button_layout_general(false, button_text, false);
        Self {
            bg: Pad::with_background(bg_color).with_clear(),
            bg_color,
            title,
            message: Child::new(message),
            alert,
            info_title: None,
            info_text: None,
            button_text,
            buttons: ButtonController::new(btn_layout),
            showing_info_screen: false,
        }
    }

    /// Adding optional info screen
    pub fn with_info_screen(mut self, info_title: &'static str, info_text: Label<&'a str>) -> Self {
        self.info_title = Some(info_title);
        self.info_text = Some(info_text);
        self.buttons = ButtonController::new(self.get_button_layout());
        self
    }

    fn has_info_screen(&self) -> bool {
        self.info_title.is_some()
    }

    fn get_button_layout(&self) -> ButtonLayout<&'static str> {
        Self::get_button_layout_general(
            self.showing_info_screen,
            self.button_text,
            self.has_info_screen(),
        )
    }

    /// Not relying on self here, to call it in constructor.
    fn get_button_layout_general(
        showing_info_screen: bool,
        button_text: &'static str,
        has_info_screen: bool,
    ) -> ButtonLayout<&'static str> {
        if showing_info_screen {
            ButtonLayout::arrow_none_none()
        } else if has_info_screen {
            ButtonLayout::cancel_armed_info(button_text)
        } else {
            ButtonLayout::cancel_none_text(button_text)
        }
    }

    /// Reflecting the current page in the buttons.
    fn update_buttons(&mut self) {
        let btn_layout = self.get_button_layout();
        self.buttons.set(btn_layout);
    }

    fn update_everything(&mut self, ctx: &mut EventCtx) {
        self.bg.clear();
        self.update_buttons();
        self.info_text.request_complete_repaint(ctx);
        self.message.request_complete_repaint(ctx);
        self.alert.request_complete_repaint(ctx);
        self.buttons.request_complete_repaint(ctx);
        self.request_complete_repaint(ctx);
    }
}

impl<'a> Component for Confirm<'a> {
    type Msg = ConfirmMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.bg.place(bounds);

        // Divide the screen into areas
        let (_title_area, minus_title) = bounds.split_top(TITLE_AREA_HEIGHT);
        let (between_title_and_buttons, button_area) = minus_title.split_bottom(BUTTON_HEIGHT);

        // Texts for the main screen
        let (message_area, alert_area) = if self.alert.is_some() {
            between_title_and_buttons.split_top(ALERT_AREA_START - TITLE_AREA_HEIGHT)
        } else {
            (between_title_and_buttons, Rect::zero())
        };
        self.message.place(message_area);
        self.alert.place(alert_area);

        // Text for the info screen
        self.info_text.place(between_title_and_buttons);

        self.buttons.place(button_area);

        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        let msg = self.buttons.event(ctx, event);
        if self.showing_info_screen {
            // Showing the info screen currently - going back with the left button
            if let Some(ButtonControllerMsg::Triggered(ButtonPos::Left)) = msg {
                self.showing_info_screen = false;
                self.update_everything(ctx);
            };
            None
        } else if self.has_info_screen() {
            // Being on the "main" screen but with an info screen available on the right
            match msg {
                Some(ButtonControllerMsg::Triggered(ButtonPos::Left)) => Some(ConfirmMsg::Cancel),
                Some(ButtonControllerMsg::Triggered(ButtonPos::Middle)) => {
                    Some(ConfirmMsg::Confirm)
                }
                Some(ButtonControllerMsg::Triggered(ButtonPos::Right)) => {
                    self.showing_info_screen = true;
                    self.update_everything(ctx);
                    None
                }
                _ => None,
            }
        } else {
            // There is just one main screen without info screen
            match msg {
                Some(ButtonControllerMsg::Triggered(ButtonPos::Left)) => Some(ConfirmMsg::Cancel),
                Some(ButtonControllerMsg::Triggered(ButtonPos::Right)) => Some(ConfirmMsg::Confirm),
                _ => None,
            }
        }
    }

    fn paint(&mut self) {
        self.bg.paint();

        let display_top_left = |text: &str| {
            display::text_top_left(Point::zero(), text, Font::BOLD, WHITE, self.bg_color);
        };

        // We are either on the info screen or on the "main" screen
        if self.showing_info_screen {
            display_top_left(unwrap!(self.info_title));
            self.info_text.paint();
        } else {
            display_top_left(self.title);
            self.message.paint();
            self.alert.paint();
        }
        self.buttons.paint();
    }

    #[cfg(feature = "ui_bounds")]
    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        self.buttons.bounds(sink);
    }
}

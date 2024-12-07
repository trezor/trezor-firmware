use crate::{
    strutil::TString,
    ui::{
        component::{Child, Component, ComponentExt, Event, EventCtx, Label, Pad},
        display::{Color, Font},
        geometry::{Point, Rect},
        shape,
        shape::Renderer,
    },
};

use super::{
    theme::{BUTTON_HEIGHT, TITLE_AREA_HEIGHT, WHITE},
    ButtonController, ButtonControllerMsg, ButtonLayout, ButtonPos,
};

const ALERT_AREA_START: i16 = 39;

#[derive(Copy, Clone)]
pub enum ConfirmMsg {
    Cancel = 1,
    Confirm = 2,
}

pub struct Confirm<'a> {
    bg: Pad,
    bg_color: Color,
    title: TString<'a>,
    message: Child<Label<'a>>,
    alert: Option<Label<'a>>,
    info_title: Option<TString<'a>>,
    info_text: Option<Label<'a>>,
    button_text: TString<'static>,
    buttons: ButtonController,
    /// Whether we are on the info screen (optional extra screen)
    showing_info_screen: bool,
    two_btn_confirm: bool,
}

impl<'a> Confirm<'a> {
    pub fn new(
        bg_color: Color,
        title: TString<'a>,
        message: Label<'a>,
        alert: Option<Label<'a>>,
        button_text: TString<'static>,
        two_btn_confirm: bool,
    ) -> Self {
        let btn_layout =
            Self::get_button_layout_general(false, button_text, false, two_btn_confirm);
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
            two_btn_confirm,
        }
    }

    /// Adding optional info screen
    pub fn with_info_screen(mut self, info_title: TString<'a>, info_text: Label<'a>) -> Self {
        self.info_title = Some(info_title);
        self.info_text = Some(info_text);
        self.buttons = ButtonController::new(self.get_button_layout());
        self
    }

    fn has_info_screen(&self) -> bool {
        self.info_title.is_some()
    }

    fn get_button_layout(&self) -> ButtonLayout {
        Self::get_button_layout_general(
            self.showing_info_screen,
            self.button_text,
            self.has_info_screen(),
            self.two_btn_confirm,
        )
    }

    /// Not relying on self here, to call it in constructor.
    fn get_button_layout_general(
        showing_info_screen: bool,
        button_text: TString<'static>,
        has_info_screen: bool,
        two_btn_confirm: bool,
    ) -> ButtonLayout {
        if showing_info_screen {
            ButtonLayout::arrow_none_none()
        } else if has_info_screen {
            ButtonLayout::cancel_armed_info(button_text)
        } else if two_btn_confirm {
            ButtonLayout::cancel_armed_none(button_text)
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

impl Component for Confirm<'_> {
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
            if let Some(ButtonControllerMsg::Triggered(ButtonPos::Left, _)) = msg {
                self.showing_info_screen = false;
                self.update_everything(ctx);
            };
            None
        } else if self.has_info_screen() {
            // Being on the "main" screen but with an info screen available on the right
            match msg {
                Some(ButtonControllerMsg::Triggered(ButtonPos::Left, _)) => {
                    Some(ConfirmMsg::Cancel)
                }
                Some(ButtonControllerMsg::Triggered(ButtonPos::Middle, _)) => {
                    Some(ConfirmMsg::Confirm)
                }
                Some(ButtonControllerMsg::Triggered(ButtonPos::Right, _)) => {
                    self.showing_info_screen = true;
                    self.update_everything(ctx);
                    None
                }
                _ => None,
            }
        } else if self.two_btn_confirm {
            match msg {
                Some(ButtonControllerMsg::Triggered(ButtonPos::Left, _)) => {
                    Some(ConfirmMsg::Cancel)
                }
                Some(ButtonControllerMsg::Triggered(ButtonPos::Middle, _)) => {
                    Some(ConfirmMsg::Confirm)
                }
                _ => None,
            }
        } else {
            // There is just one main screen without info screen
            match msg {
                Some(ButtonControllerMsg::Triggered(ButtonPos::Left, _)) => {
                    Some(ConfirmMsg::Cancel)
                }
                Some(ButtonControllerMsg::Triggered(ButtonPos::Right, _)) => {
                    Some(ConfirmMsg::Confirm)
                }
                _ => None,
            }
        }
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.bg.render(target);

        let mut display_top_left = |text: TString| {
            text.map(|t| {
                shape::Text::new(Point::zero(), t)
                    .with_font(Font::BOLD)
                    .with_fg(WHITE)
                    .render(target);
            });
        };

        // We are either on the info screen or on the "main" screen
        if self.showing_info_screen {
            if let Some(title) = self.info_title {
                display_top_left(title);
            }
            self.info_text.render(target);
        } else {
            display_top_left(self.title);
            self.message.render(target);
            self.alert.render(target);
        }
        self.buttons.render(target);
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for Confirm<'_> {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("BlConfirm");
    }
}

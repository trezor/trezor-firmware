use super::super::theme::bootloader::{BUTTON_HEIGHT, TEXT_BOLD, TITLE_AREA_HEIGHT};
use super::buttons::{Button, ButtonPos, Buttons};
use super::menu::{Menu, MenuSelection};
use crate::strutil::TString;
use crate::ui::component::{Component, ComponentExt, Event, EventCtx, Label, Pad};
use crate::ui::display::Color;
use crate::ui::geometry::Rect;
use crate::ui::shape::Renderer;

const ALERT_AREA_START: i16 = 39;

#[derive(Copy, Clone)]
pub enum ConfirmMsg {
    Cancel = 1,
    Confirm = 2,
}

/// Context menu with the info item and cancel.
type ConfirmMenu = Menu<2>;
const MENU_INFO: usize = 0;

#[derive(Copy, Clone, PartialEq)]
enum ConfirmState {
    Main,
    /// Context menu opened by the left button
    Menu,
    /// Info screen opened from the context menu
    Info,
}

pub struct Confirm<'a> {
    bg: Pad,
    title: Label<'a>,
    message: Label<'a>,
    alert: Option<Label<'a>>,
    /// Name of the context menu item opening the info screen
    info_name: Option<&'static str>,
    info_title: Option<Label<'a>>,
    info_text: Option<Label<'a>>,
    menu: Option<ConfirmMenu>,
    button_text: &'static str,
    buttons: Buttons,
    state: ConfirmState,
}

impl<'a> Confirm<'a> {
    /// Confirmation with a cancel cross on the left and both buttons
    /// confirming.
    pub fn new(
        bg_color: Color,
        title: TString<'a>,
        message: Label<'a>,
        alert: Option<Label<'a>>,
        button_text: &'static str,
    ) -> Self {
        let mut confirm = Self {
            bg: Pad::with_background(bg_color).with_clear(),
            title: Label::left_aligned(title, TEXT_BOLD),
            message,
            alert,
            info_name: None,
            info_title: None,
            info_text: None,
            menu: None,
            button_text,
            buttons: Buttons::new(None, None, None),
            state: ConfirmState::Main,
        };
        confirm.set_buttons();
        confirm
    }

    /// Adding a context menu on the left with an info screen and cancel. The
    /// right button confirms.
    pub fn with_menu(
        mut self,
        info_name: &'static str,
        info_title: TString<'a>,
        info_text: Label<'a>,
    ) -> Self {
        self.info_name = Some(info_name);
        self.info_title = Some(Label::left_aligned(info_title, TEXT_BOLD));
        self.info_text = Some(info_text);
        self.set_buttons();
        self
    }

    fn new_menu(info_name: &'static str) -> ConfirmMenu {
        Menu::new([info_name, "Cancel"])
    }

    fn set_buttons(&mut self) {
        let (left, middle, right) = match self.state {
            ConfirmState::Main if self.info_name.is_some() => {
                (Button::menu(), None, Some(Button::Text(self.button_text)))
            }
            ConfirmState::Main => (
                Button::cancel(),
                Some(Button::ArmedText(self.button_text)),
                None,
            ),
            // The menu has its own buttons
            ConfirmState::Menu | ConfirmState::Info => (Button::cancel(), None, None),
        };
        self.buttons.set(Some(left), middle, right);
    }

    fn set_state(&mut self, ctx: &mut EventCtx, state: ConfirmState) {
        self.state = state;
        self.bg.clear();
        self.set_buttons();
        self.request_complete_repaint(ctx);
    }

    fn event_main(&mut self, ctx: &mut EventCtx, event: Event) -> Option<ConfirmMsg> {
        match self.buttons.event(ctx, event) {
            Some(ButtonPos::Left) => {
                let Some(info_name) = self.info_name else {
                    return Some(ConfirmMsg::Cancel);
                };
                // The menu always opens on its first item
                let mut menu = Self::new_menu(info_name);
                menu.place(self.bg.area);
                self.menu = Some(menu);
                self.set_state(ctx, ConfirmState::Menu);
                None
            }
            Some(ButtonPos::Middle | ButtonPos::Right) => Some(ConfirmMsg::Confirm),
            None => None,
        }
    }
}

impl Component for Confirm<'_> {
    type Msg = ConfirmMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.bg.place(bounds);

        // Divide the screen into areas
        let (title_area, minus_title) = bounds.split_top(TITLE_AREA_HEIGHT);
        let (between_title_and_buttons, button_area) = minus_title.split_bottom(BUTTON_HEIGHT);

        // Texts for the main screen
        let (message_area, alert_area) = if self.alert.is_some() {
            between_title_and_buttons.split_top(ALERT_AREA_START - TITLE_AREA_HEIGHT)
        } else {
            (between_title_and_buttons, Rect::zero())
        };
        self.title.place(title_area);
        self.message.place(message_area);
        self.alert.place(alert_area);

        // Text for the info screen
        self.info_title.place(title_area);
        self.info_text.place(between_title_and_buttons);

        self.menu.place(bounds);
        self.buttons.place(button_area);

        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        match self.state {
            ConfirmState::Main => self.event_main(ctx, event),
            ConfirmState::Menu => {
                match self.menu.event(ctx, event) {
                    Some(MenuSelection::Close) => self.set_state(ctx, ConfirmState::Main),
                    Some(MenuSelection::Item(MENU_INFO)) => self.set_state(ctx, ConfirmState::Info),
                    Some(MenuSelection::Item(_)) => return Some(ConfirmMsg::Cancel),
                    None => {}
                }
                None
            }
            ConfirmState::Info => {
                // Going back to the menu with the cross
                if let Some(ButtonPos::Left) = self.buttons.event(ctx, event) {
                    self.set_state(ctx, ConfirmState::Menu);
                }
                None
            }
        }
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.bg.render(target);

        match self.state {
            ConfirmState::Main => {
                self.title.render(target);
                self.message.render(target);
                self.alert.render(target);
                self.buttons.render(target);
            }
            ConfirmState::Menu => self.menu.render(target),
            ConfirmState::Info => {
                self.info_title.render(target);
                self.info_text.render(target);
                self.buttons.render(target);
            }
        }
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for Confirm<'_> {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("BlConfirm");
    }
}

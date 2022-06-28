use super::{common::ButtonDetails, theme, Button, ButtonPos, ButtonStyleSheet};
use crate::{
    time::Duration,
    ui::{
        component::{base::Event, Component, EventCtx, TimerToken},
        event::{ButtonEvent, PhysicalButton},
        geometry::Rect,
    },
};

#[derive(Copy, Clone, PartialEq, Eq)]
enum ButtonState {
    Nothing,
    OneDown(PhysicalButton),
    BothDown,
    OneReleased(PhysicalButton),
}

pub enum ButtonControllerMsg {
    Triggered(ButtonPos),
}

/// Wrapping a button and its active state, so that it can be easily
/// shown/hidden according to `is_active`.
pub struct ButtonContainer<T> {
    button: Button<T>,
    is_active: bool,
}

impl<T: AsRef<str>> ButtonContainer<T> {
    pub fn new(pos: ButtonPos, text: T, styles: ButtonStyleSheet, is_active: bool) -> Self {
        Self {
            button: Button::with_text(pos, text, styles),
            is_active,
        }
    }

    pub fn reacts_to_single_click(&self) -> bool {
        self.is_active && !self.button.is_longpress()
    }

    pub fn get_longpress(&self) -> Option<Duration> {
        if self.is_active {
            self.button.get_longpress()
        } else {
            None
        }
    }

    /// Changing the state of the button.
    /// Passing `None` will mark the button as inactive.
    pub fn set(&mut self, btn_details: Option<ButtonDetails<T>>, button_area: Rect) {
        if let Some(btn_details) = btn_details {
            self.button.set_text(btn_details.text, button_area);
            self.button.set_long_press(btn_details.duration);
            self.is_active = true;
        } else {
            self.is_active = false;
        }
    }
}

/// Component responsible for handling buttons.
///
/// Acts as a state-machine of `ButtonState`.
///
/// Storing all three possible buttons - left, middle and right -
/// and handling their placement, painting and returning
/// appropriate events when they are triggered.
///
/// Buttons can be interactively changed by clients by appropriate
/// `set_XXX()` methods.
///
/// Only "final" button events are returned in `ButtonControllerMsg::Triggered`,
/// based upon the buttons being long-press or not.
pub struct ButtonController<T> {
    left_btn: ButtonContainer<T>,
    middle_btn: ButtonContainer<T>,
    right_btn: ButtonContainer<T>,
    state: ButtonState,
    long_timer: Option<TimerToken>,
    // Button area is needed so the buttons
    // can be "re-placed" after their text is changed
    // Will be set in `place`
    button_area: Rect,
}

impl ButtonController<&'static str> {
    /// Supplying `None` marks the appropriate button inactive.
    pub fn new(
        left_text: Option<&'static str>,
        mid_text: Option<&'static str>,
        right_text: Option<&'static str>,
    ) -> Self {
        Self {
            left_btn: ButtonContainer::new(
                ButtonPos::Left,
                left_text.unwrap_or("LEFT"),
                theme::button_default(),
                left_text.is_some(),
            ),
            middle_btn: ButtonContainer::new(
                ButtonPos::Middle,
                mid_text.unwrap_or("MID"),
                theme::button_default(),
                mid_text.is_some(),
            ),
            right_btn: ButtonContainer::new(
                ButtonPos::Right,
                right_text.unwrap_or("RIGHT"),
                theme::button_default(),
                right_text.is_some(),
            ),
            state: ButtonState::Nothing,
            long_timer: None,
            button_area: Rect::zero(),
        }
    }
}

impl<T: AsRef<str>> ButtonController<T> {
    pub fn set_left(&mut self, btn_details: Option<ButtonDetails<T>>) {
        self.left_btn.set(btn_details, self.button_area);
    }

    pub fn set_right(&mut self, btn_details: Option<ButtonDetails<T>>) {
        self.right_btn.set(btn_details, self.button_area);
    }

    pub fn set_middle(&mut self, btn_details: Option<ButtonDetails<T>>) {
        self.middle_btn.set(btn_details, self.button_area);
    }
}

impl<T: AsRef<str>> Component for ButtonController<T> {
    type Msg = ButtonControllerMsg;

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        match event {
            Event::Button(button) => {
                let (new_state, event) = match self.state {
                    ButtonState::Nothing => match button {
                        ButtonEvent::ButtonPressed(which) => {
                            // Starting the timer if button is a long press
                            match which {
                                PhysicalButton::Left => {
                                    if let Some(duration) = self.left_btn.get_longpress() {
                                        self.long_timer = Some(ctx.request_timer(duration));
                                    }
                                }
                                PhysicalButton::Right => {
                                    if let Some(duration) = self.right_btn.get_longpress() {
                                        self.long_timer = Some(ctx.request_timer(duration));
                                    }
                                }
                                _ => {}
                            }
                            (ButtonState::OneDown(which), None)
                        }
                        _ => (self.state, None),
                    },
                    ButtonState::OneDown(which_down) => match button {
                        ButtonEvent::ButtonReleased(b) if b == which_down => match which_down {
                            PhysicalButton::Left => (
                                ButtonState::Nothing,
                                if self.left_btn.reacts_to_single_click() {
                                    Some(ButtonControllerMsg::Triggered(ButtonPos::Left))
                                } else {
                                    None
                                },
                            ),
                            PhysicalButton::Right => (
                                ButtonState::Nothing,
                                if self.right_btn.reacts_to_single_click() {
                                    Some(ButtonControllerMsg::Triggered(ButtonPos::Right))
                                } else {
                                    None
                                },
                            ),
                            _ => (ButtonState::Nothing, None),
                        },

                        ButtonEvent::ButtonPressed(b) if b != which_down => {
                            if let Some(duration) = self.middle_btn.button.get_longpress() {
                                self.long_timer = Some(ctx.request_timer(duration));
                            }
                            (ButtonState::BothDown, None)
                        }
                        _ => (self.state, None),
                    },
                    ButtonState::BothDown => match button {
                        ButtonEvent::ButtonReleased(b) => (ButtonState::OneReleased(b), None),
                        _ => (self.state, None),
                    },
                    ButtonState::OneReleased(which_up) => match button {
                        ButtonEvent::ButtonPressed(b) if b == which_up => {
                            (ButtonState::BothDown, None)
                        }
                        ButtonEvent::ButtonReleased(b) if b != which_up => (
                            ButtonState::Nothing,
                            if self.middle_btn.reacts_to_single_click() {
                                Some(ButtonControllerMsg::Triggered(ButtonPos::Middle))
                            } else {
                                None
                            },
                        ),
                        _ => (self.state, None),
                    },
                };
                self.state = new_state;
                event
            }
            Event::Timer(token) if self.long_timer == Some(token) => {
                // Handling hold-to-confirm (long-press) buttons
                self.long_timer = None;
                let which_button = match self.state {
                    ButtonState::OneDown(PhysicalButton::Left) => Some(ButtonPos::Left),
                    ButtonState::OneDown(PhysicalButton::Right) => Some(ButtonPos::Right),
                    ButtonState::BothDown | ButtonState::OneReleased(_) => Some(ButtonPos::Middle),
                    _ => None,
                };
                self.state = ButtonState::Nothing;
                which_button.map(ButtonControllerMsg::Triggered)
            }
            _ => None,
        }
    }

    fn paint(&mut self) {
        let highlight = match self.state {
            ButtonState::Nothing => None,
            ButtonState::OneDown(down_button) => match down_button {
                PhysicalButton::Left => Some(ButtonPos::Left),
                PhysicalButton::Right => Some(ButtonPos::Right),
                _ => None,
            },
            ButtonState::BothDown | ButtonState::OneReleased(_) => Some(ButtonPos::Middle),
        };
        if self.left_btn.is_active {
            self.left_btn
                .button
                .paint_pressed(matches!(highlight, Some(ButtonPos::Left)));
        }
        if self.middle_btn.is_active {
            self.middle_btn
                .button
                .paint_pressed(matches!(highlight, Some(ButtonPos::Middle)));
        }
        if self.right_btn.is_active {
            self.right_btn
                .button
                .paint_pressed(matches!(highlight, Some(ButtonPos::Right)));
        }
    }

    fn place(&mut self, bounds: Rect) -> Rect {
        // Saving button area so that we can re-place the buttons
        // when when they get updated
        self.button_area = bounds;
        if self.left_btn.is_active {
            self.left_btn.button.place(bounds);
        }
        if self.middle_btn.is_active {
            self.middle_btn.button.place(bounds);
        }
        if self.right_btn.is_active {
            self.right_btn.button.place(bounds);
        }
        bounds
    }
}

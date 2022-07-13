use super::{
    common::ButtonDetails, common::ButtonLayout, theme, Button, ButtonPos, HoldToConfirm,
    HoldToConfirmMsg,
};
use crate::ui::component::{ComponentExt, Pad};
use crate::{
    time::Duration,
    ui::{
        component::{base::Event, Child, Component, EventCtx},
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

// TODO: could have the possibility of `Both`,
// so that button can be single-clicked or held longer time,
// with different behavior
pub enum ButtonType {
    Nothing,
    NormalButton,
    HoldToConfirm,
}

impl ButtonType {
    pub fn from_button_details<T: AsRef<str>>(details: Option<ButtonDetails<T>>) -> Self {
        if let Some(details) = details {
            if details.duration.is_some() {
                Self::HoldToConfirm
            } else {
                Self::NormalButton
            }
        } else {
            Self::Nothing
        }
    }
}

/// Wrapping a button and its state, so that it can be easily
/// controlled from outside.
///
/// Users have a choice of a normal button or Hold-to-confirm button.
/// `button_type` specified what from those two is used, if anything.
pub struct ButtonContainer<T> {
    // TODO: it is not great that we have to store the components as
    // `Option`s, because their handling is then more complex
    // (it is enough to have the `button_type` saying whether to use it or not).
    // However, to set all the components to "something", we would need the
    // `text` of the components, and we cannot get a default value for it
    // (the default value for T: AsRef<str>) in case it is currently missing.
    button: Option<Child<Button<T>>>,
    hold_to_confirm: Option<Child<HoldToConfirm<T>>>,
    pos: ButtonPos, // so that we can create the button later with correct position
    button_type: ButtonType,
    btn_details: Option<ButtonDetails<T>>,
}

impl<T: Clone + AsRef<str>> ButtonContainer<T> {
    /// Supplying `None` as `btn_details`  marks the button inactive
    /// (it can be later activated in `set()`).
    pub fn new(pos: ButtonPos, btn_details: Option<ButtonDetails<T>>) -> Self {
        let button = btn_details
            .clone()
            .map(|btn_details| Self::get_button(pos, btn_details));
        let hold_to_confirm = btn_details
            .clone()
            .map(|btn_details| Self::get_hold_to_confirm(pos, btn_details));

        Self {
            button,
            hold_to_confirm,
            pos,
            button_type: ButtonType::from_button_details(btn_details.clone()),
            btn_details,
        }
    }

    /// Create `Button` component from `btn_details`.
    fn get_button(pos: ButtonPos, btn_details: ButtonDetails<T>) -> Child<Button<T>> {
        Child::new(Button::with_text(
            pos,
            btn_details.clone().text,
            btn_details.style(),
        ))
    }

    /// Create `HoldToConfirm` component from `btn_details`.
    fn get_hold_to_confirm(
        pos: ButtonPos,
        btn_details: ButtonDetails<T>,
    ) -> Child<HoldToConfirm<T>> {
        let duration = btn_details
            .duration
            .unwrap_or_else(|| Duration::from_millis(1000));
        Child::new(HoldToConfirm::new(
            pos,
            btn_details.text,
            theme::loader_bold(),
            duration,
        ))
    }

    /// Changing the state of the button.
    ///
    /// Setting the appropriate `button_type` and updating the
    /// appropriate component.
    ///
    /// Passing `None` as `btn_details` will mark the button as inactive.
    pub fn set(
        &mut self,
        ctx: &mut EventCtx,
        btn_details: Option<ButtonDetails<T>>,
        button_area: Rect,
    ) {
        // Saving the current button details for comparison with next state.
        self.btn_details = btn_details.clone();

        if let Some(btn_details) = btn_details {
            // Choosing between Hold-to-confirm and normal button based on `duration`.
            // Creating the appropriate button if it does not exist and updating
            // it to match the current btn_details.
            // Even when button is freshly created, it needs to be updated,
            // because it is not placed and that happens during `set_text()`.
            if let Some(duration) = btn_details.duration {
                self.button_type = ButtonType::HoldToConfirm;
                if self.hold_to_confirm.is_none() {
                    self.hold_to_confirm =
                        Some(Self::get_hold_to_confirm(self.pos, btn_details.clone()));
                }

                if let Some(hold_to_confirm) = &mut self.hold_to_confirm {
                    hold_to_confirm.mutate(ctx, |_ctx, btn| {
                        btn.set_text(btn_details.text, button_area);
                        btn.set_duration(duration);
                    });
                    hold_to_confirm.request_complete_repaint(ctx);
                }
            } else {
                self.button_type = ButtonType::NormalButton;
                if self.button.is_none() {
                    self.button = Some(Self::get_button(self.pos, btn_details.clone()));
                }

                if let Some(button) = &mut self.button {
                    let style = btn_details.style();
                    button.mutate(ctx, |_ctx, btn| {
                        btn.set_text(btn_details.text, button_area);
                        btn.set_style(style);
                    });
                    button.request_complete_repaint(ctx);
                }
            }
        } else {
            self.button_type = ButtonType::Nothing;
        }
    }

    /// Placing both possible components.
    /// For next updates, the "new" buttons are places inside `Button::set_text()`
    pub fn place(&mut self, bounds: Rect) {
        if let Some(button) = self.button.as_mut() {
            button.place(bounds);
        };
        if let Some(hold_to_confirm) = self.hold_to_confirm.as_mut() {
            hold_to_confirm.place(bounds);
        };
    }

    /// Painting the component that should be currently visible, if any.
    pub fn paint(&mut self) {
        if matches!(self.button_type, ButtonType::NormalButton) {
            if let Some(button) = self.button.as_mut() {
                button.paint();
            };
        } else if matches!(self.button_type, ButtonType::HoldToConfirm) {
            if let Some(hold_to_confirm) = self.hold_to_confirm.as_mut() {
                hold_to_confirm.paint();
            };
        }
    }

    /// Setting the visual state of the button - released/pressed.
    pub fn set_pressed(&mut self, ctx: &mut EventCtx, is_pressed: bool) {
        if let Some(button) = &mut self.button {
            button.mutate(ctx, |ctx, btn| {
                btn.set_pressed(ctx, is_pressed);
            });
        }
    }

    /// Whether single-click should trigger action.
    pub fn reacts_to_single_click(&self) -> bool {
        matches!(self.button_type, ButtonType::NormalButton)
    }

    /// Whether hold-to-confirm was triggered.
    /// If so, also resetting the state of the button.
    pub fn hold_to_confirm_triggered(&mut self, ctx: &mut EventCtx, event: Event) -> bool {
        if matches!(self.button_type, ButtonType::HoldToConfirm) {
            let msg = self.hold_to_confirm.event(ctx, event);
            if matches!(msg, Some(HoldToConfirmMsg::Confirmed)) {
                if let Some(hold_to_confirm) = &mut self.hold_to_confirm {
                    hold_to_confirm.inner_mut().reset();
                    hold_to_confirm.request_complete_repaint(ctx);
                    return true;
                }
            }
        };
        false
    }

    /// Whether newly supplied button details are different from the
    /// current one.
    pub fn is_changing(&self, btn_details: Option<ButtonDetails<T>>) -> bool {
        if btn_details.is_some() && self.btn_details.is_some() {
            btn_details.as_ref().unwrap().id() != self.btn_details.as_ref().unwrap().id()
        } else {
            btn_details.is_some() != self.btn_details.is_some()
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
/// Buttons can be interactively changed by clients by `set()`.
///
/// Only "final" button events are returned in `ButtonControllerMsg::Triggered`,
/// based upon the buttons being long-press or not.
pub struct ButtonController<T> {
    pad: Pad,
    left_btn: ButtonContainer<T>,
    middle_btn: ButtonContainer<T>,
    right_btn: ButtonContainer<T>,
    state: ButtonState,
    // Button area is needed so the buttons
    // can be "re-placed" after their text is changed
    // Will be set in `place`
    button_area: Rect,
}

impl<T: Clone + AsRef<str>> ButtonController<T> {
    pub fn new(btn_layout: ButtonLayout<T>) -> Self {
        Self {
            pad: Pad::with_background(theme::BG).with_clear(),
            left_btn: ButtonContainer::new(ButtonPos::Left, btn_layout.btn_left),
            middle_btn: ButtonContainer::new(ButtonPos::Middle, btn_layout.btn_middle),
            right_btn: ButtonContainer::new(ButtonPos::Right, btn_layout.btn_right),
            state: ButtonState::Nothing,
            button_area: Rect::zero(),
        }
    }

    /// If any button changed from previous state, updating all of them,
    /// otherwise not doing anything not to flicker the screen.
    pub fn set(&mut self, ctx: &mut EventCtx, btn_layout: ButtonLayout<T>) {
        // TODO: investigate how to make just one button to be repainted
        // Tried to add pad to each and clear it on any change but not successful
        // (I maybe forgot to paint the pad...)
        let left = btn_layout.btn_left;
        let middle = btn_layout.btn_middle;
        let right = btn_layout.btn_right;
        if self.buttons_have_changed(left.clone(), middle.clone(), right.clone()) {
            self.left_btn.set(ctx, left, self.button_area);
            self.middle_btn.set(ctx, middle, self.button_area);
            self.right_btn.set(ctx, right, self.button_area);
            self.pad.clear();
        }
    }

    /// Find out if any of our buttons has changed.
    fn buttons_have_changed(
        &mut self,
        left: Option<ButtonDetails<T>>,
        mid: Option<ButtonDetails<T>>,
        right: Option<ButtonDetails<T>>,
    ) -> bool {
        self.left_btn.is_changing(left)
            || self.middle_btn.is_changing(mid)
            || self.right_btn.is_changing(right)
    }

    /// Setting the pressed state for all three buttons by boolean flags.
    fn set_pressed(&mut self, ctx: &mut EventCtx, left: bool, mid: bool, right: bool) {
        self.left_btn.set_pressed(ctx, left);
        self.middle_btn.set_pressed(ctx, mid);
        self.right_btn.set_pressed(ctx, right);
    }
}

impl<T: Clone + AsRef<str>> Component for ButtonController<T> {
    type Msg = ButtonControllerMsg;

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        // Handling the hold_to_confirm elements
        if self.left_btn.hold_to_confirm_triggered(ctx, event) {
            return Some(ButtonControllerMsg::Triggered(ButtonPos::Left));
        }
        if self.middle_btn.hold_to_confirm_triggered(ctx, event) {
            return Some(ButtonControllerMsg::Triggered(ButtonPos::Middle));
        }
        if self.right_btn.hold_to_confirm_triggered(ctx, event) {
            return Some(ButtonControllerMsg::Triggered(ButtonPos::Right));
        }

        // State machine for the ButtonController
        match event {
            Event::Button(button) => {
                let (new_state, event) = match self.state {
                    ButtonState::Nothing => match button {
                        ButtonEvent::ButtonPressed(which) => (ButtonState::OneDown(which), None),
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

                // Updating the visual feedback for the buttons
                match new_state {
                    ButtonState::Nothing => {
                        self.set_pressed(ctx, false, false, false);
                    }
                    ButtonState::OneDown(down_button) => match down_button {
                        PhysicalButton::Left => {
                            self.set_pressed(ctx, true, false, false);
                        }
                        PhysicalButton::Right => {
                            self.set_pressed(ctx, false, false, true);
                        }
                        _ => {}
                    },
                    ButtonState::BothDown | ButtonState::OneReleased(_) => {
                        self.set_pressed(ctx, false, true, false);
                    }
                };

                self.state = new_state;
                event
            }
            _ => None,
        }
    }

    fn paint(&mut self) {
        self.pad.paint();
        self.left_btn.paint();
        self.middle_btn.paint();
        self.right_btn.paint();
    }

    fn place(&mut self, bounds: Rect) -> Rect {
        // Saving button area so that we can re-place the buttons
        // when they get updated
        self.button_area = bounds;

        self.pad.place(bounds);
        self.left_btn.place(bounds);
        self.middle_btn.place(bounds);
        self.right_btn.place(bounds);

        bounds
    }
}

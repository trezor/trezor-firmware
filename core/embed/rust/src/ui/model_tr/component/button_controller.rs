use super::{
    common::ButtonDetails, common::ButtonLayout, theme, Button, ButtonPos, ButtonStyleSheet,
    HoldToConfirm, HoldToConfirmMsg, LoaderStyleSheet,
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
/// controller from outside.
///
/// Users have a choice of a normal button or Hold-to-confirm button.
/// `button_type` specified what from those two is used, if anything.
pub struct ButtonContainer<T> {
    button: Child<Button<T>>,
    hold_to_confirm: Child<HoldToConfirm<T>>,
    button_type: ButtonType,
    button_details: Option<ButtonDetails<T>>,
}

impl ButtonContainer<&'static str> {
    /// Supplying `None` marks the appropriate button inactive.
    pub fn from_button_details(
        pos: ButtonPos,
        btn_details: Option<ButtonDetails<&'static str>>,
    ) -> Self {
        Self::new(
            pos,
            btn_details
                .unwrap_or_else(|| ButtonDetails::new("TEXT"))
                .text,
            btn_details
                .unwrap_or_else(|| ButtonDetails::new("normal style"))
                .style(),
            theme::loader_bold(),
            ButtonType::from_button_details(btn_details),
            btn_details,
        )
    }
}

impl<T: Clone + AsRef<str>> ButtonContainer<T> {
    pub fn new(
        pos: ButtonPos,
        text: T,
        button_styles: ButtonStyleSheet,
        loader_styles: LoaderStyleSheet,
        button_type: ButtonType,
        button_details: Option<ButtonDetails<T>>,
    ) -> Self {
        Self {
            button: Child::new(Button::with_text(pos, text.clone(), button_styles)),
            hold_to_confirm: Child::new(HoldToConfirm::new(
                pos,
                text,
                loader_styles,
                Duration::from_millis(1000),
            )),
            button_type,
            button_details,
        }
    }

    /// Changing the state of the button.
    /// Passing `None` as `btn_details` will mark the button as inactive.
    pub fn set(
        &mut self,
        ctx: &mut EventCtx,
        btn_details: Option<ButtonDetails<T>>,
        button_area: Rect,
    ) {
        // Saving the current button details for comparison with next state.
        self.button_details = btn_details.clone();

        if let Some(btn_details) = btn_details {
            // Choosing between Hold-to-confirm and normal button based on `duration`
            if let Some(duration) = btn_details.duration {
                self.hold_to_confirm.mutate(ctx, |_ctx, btn| {
                    btn.set_text(btn_details.text, button_area);
                    btn.set_duration(duration);
                });
                self.hold_to_confirm.request_complete_repaint(ctx);
                self.button_type = ButtonType::HoldToConfirm;
            } else {
                let style = btn_details.style();
                self.button.mutate(ctx, |_ctx, btn| {
                    btn.set_text(btn_details.text, button_area);
                    btn.set_style(style);
                });
                self.button.request_complete_repaint(ctx);
                self.button_type = ButtonType::NormalButton;
            }
        } else {
            self.button_type = ButtonType::Nothing;
        }
    }

    /// Placing both possible components
    pub fn place(&mut self, bounds: Rect) {
        self.button.place(bounds);
        self.hold_to_confirm.place(bounds);
    }

    /// Painting the component that should be currently visible, if any
    pub fn paint(&mut self) {
        if matches!(self.button_type, ButtonType::NormalButton) {
            self.button.paint();
        } else if matches!(self.button_type, ButtonType::HoldToConfirm) {
            self.hold_to_confirm.paint();
        }
    }

    /// Setting the visual state of the button - released/pressed
    pub fn set_pressed(&mut self, ctx: &mut EventCtx, is_pressed: bool) {
        self.button.mutate(ctx, |ctx, btn| {
            btn.set_pressed(ctx, is_pressed);
        });
    }

    /// Whether single-click should trigger action.
    pub fn reacts_to_single_click(&self) -> bool {
        matches!(self.button_type, ButtonType::NormalButton)
    }

    /// Whether hold-to-confirm was triggered
    /// If so, also resetting the state of the button
    pub fn hold_to_confirm_triggered(&mut self, ctx: &mut EventCtx, event: Event) -> bool {
        if matches!(self.button_type, ButtonType::HoldToConfirm) {
            let msg = self.hold_to_confirm.event(ctx, event);
            if matches!(msg, Some(HoldToConfirmMsg::Confirmed)) {
                self.hold_to_confirm.inner_mut().reset();
                self.hold_to_confirm.request_complete_repaint(ctx);
                return true;
            }
        };
        false
    }

    /// Whether newly supplied button details are different from the
    /// current one.
    pub fn is_changing(&self, btn_details: Option<ButtonDetails<T>>) -> bool {
        if btn_details.is_some() && self.button_details.is_some() {
            btn_details.as_ref().unwrap().id() != self.button_details.as_ref().unwrap().id()
        } else {
            btn_details.is_some() != self.button_details.is_some()
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

impl ButtonController<&'static str> {
    pub fn new(btn_layout: ButtonLayout<&'static str>) -> Self {
        Self {
            pad: Pad::with_background(theme::BG).with_clear(),
            left_btn: ButtonContainer::from_button_details(ButtonPos::Left, btn_layout.btn_left),
            middle_btn: ButtonContainer::from_button_details(
                ButtonPos::Middle,
                btn_layout.btn_middle,
            ),
            right_btn: ButtonContainer::from_button_details(ButtonPos::Right, btn_layout.btn_right),
            state: ButtonState::Nothing,
            button_area: Rect::zero(),
        }
    }
}

impl<T: Clone + AsRef<str>> ButtonController<T> {
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
        // when when they get updated
        self.button_area = bounds;

        self.pad.place(bounds);
        self.left_btn.place(bounds);
        self.middle_btn.place(bounds);
        self.right_btn.place(bounds);

        bounds
    }
}

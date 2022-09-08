use super::{
    theme, Button, ButtonContent, ButtonDetails, ButtonLayout, ButtonPos, HoldToConfirm,
    HoldToConfirmMsg, LoaderStyleSheet,
};
use crate::{
    time::Duration,
    ui::{
        component::{base::Event, Child, Component, ComponentExt, EventCtx, Pad},
        event::{ButtonEvent, PhysicalButton},
        geometry::Rect,
    },
};

use heapless::String;

#[derive(Copy, Clone, PartialEq, Eq)]
enum ButtonState {
    Nothing,
    OneDown(PhysicalButton),
    BothDown,
    OneReleased(PhysicalButton),
    HTCNeedsRelease(PhysicalButton),
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
    // TODO: create enum of either Button or HTC
    button: Option<Child<Button<T>>>,
    hold_to_confirm: Option<Child<HoldToConfirm<T>>>,
    /// Stored to create the button later with correct position
    pos: ButtonPos,
    button_type: ButtonType,
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
            button_type: ButtonType::from_button_details(btn_details),
        }
    }

    /// Create `Button` component from `btn_details`.
    fn get_button(pos: ButtonPos, btn_details: ButtonDetails<T>) -> Child<Button<T>> {
        // Deciding between text and icon
        if let Some(text) = btn_details.clone().text {
            Child::new(Button::with_text(pos, text, btn_details.style()))
        } else if let Some(icon) = btn_details.icon {
            Child::new(Button::with_icon(pos, icon, btn_details.style()))
        } else {
            panic!("ButtonContainer: no text or icon provided");
        }
    }

    /// Create `HoldToConfirm` component from `btn_details`.
    fn get_hold_to_confirm(
        pos: ButtonPos,
        btn_details: ButtonDetails<T>,
    ) -> Child<HoldToConfirm<T>> {
        let duration = btn_details
            .duration
            .unwrap_or_else(|| Duration::from_millis(1000));
        if let Some(text) = btn_details.text {
            Child::new(HoldToConfirm::text(
                pos,
                text,
                LoaderStyleSheet::default(),
                duration,
            ))
        } else if let Some(icon) = btn_details.icon {
            Child::new(HoldToConfirm::icon(
                pos,
                icon,
                LoaderStyleSheet::default(),
                duration,
            ))
        } else {
            panic!("ButtonContainer: no text or icon provided");
        }
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
        if let Some(btn_details) = btn_details {
            // Choosing between Hold-to-confirm and normal button based on `duration`.
            // Creating and placing the appropriate button if it does
            // not exist and updating it to match the current btn_details.
            if let Some(duration) = btn_details.duration {
                self.button_type = ButtonType::HoldToConfirm;
                if self.hold_to_confirm.is_none() {
                    self.hold_to_confirm =
                        Some(Self::get_hold_to_confirm(self.pos, btn_details.clone()));
                    self.hold_to_confirm.place(button_area);
                }

                if let Some(hold_to_confirm) = &mut self.hold_to_confirm {
                    hold_to_confirm.mutate(ctx, |_ctx, btn| {
                        // Deciding between text and icon
                        if let Some(text) = btn_details.text {
                            btn.set_text(text, button_area);
                        } else if let Some(_icon) = btn_details.icon {
                            todo!("support icon for HoldToConfirm");
                        }
                        btn.set_duration(duration);
                    });
                    hold_to_confirm.request_complete_repaint(ctx);
                }
            } else {
                self.button_type = ButtonType::NormalButton;
                if self.button.is_none() {
                    self.button = Some(Self::get_button(self.pos, btn_details.clone()));
                    self.button.place(button_area);
                }

                if let Some(button) = &mut self.button {
                    let style = btn_details.style();
                    button.mutate(ctx, |_ctx, btn| {
                        // Deciding between text and icon
                        if let Some(text) = btn_details.text {
                            btn.set_text(text);
                        } else if let Some(icon) = btn_details.icon {
                            btn.set_icon(icon);
                        }
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

    /// Find out whether hold-to-confirm was triggered.
    pub fn htc_got_triggered(&mut self, ctx: &mut EventCtx, event: Event) -> bool {
        if matches!(self.button_type, ButtonType::HoldToConfirm) {
            let msg = self.hold_to_confirm.event(ctx, event);
            if matches!(msg, Some(HoldToConfirmMsg::Confirmed)) {
                // TODO: consider whether to reset and repaint the button or not
                // Got deleted because of the wipe screen where it was better to not do that.
                return true;
            }
        };
        false
    }

    /// Registering hold event.
    pub fn hold_started(&mut self, ctx: &mut EventCtx) {
        self.send_htc_event(ctx, Event::Button(ButtonEvent::HoldStarted));
    }

    /// Cancelling hold event.
    pub fn hold_ended(&mut self, ctx: &mut EventCtx) {
        self.send_htc_event(ctx, Event::Button(ButtonEvent::HoldEnded));
    }

    /// Sending hold-to-confirm event in case the current button is HTC.
    fn send_htc_event(&mut self, ctx: &mut EventCtx, event: Event) {
        if matches!(self.button_type, ButtonType::HoldToConfirm) {
            if let Some(hold_to_confirm) = &mut self.hold_to_confirm {
                hold_to_confirm.event(ctx, event);
            }
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

    /// Updating all the three buttons to the wanted states.
    pub fn set(&mut self, ctx: &mut EventCtx, btn_layout: ButtonLayout<T>) {
        self.left_btn
            .set(ctx, btn_layout.btn_left, self.button_area);
        self.middle_btn
            .set(ctx, btn_layout.btn_middle, self.button_area);
        self.right_btn
            .set(ctx, btn_layout.btn_right, self.button_area);
        self.pad.clear();
    }

    /// Setting the pressed state for all three buttons by boolean flags.
    fn set_pressed(&mut self, ctx: &mut EventCtx, left: bool, mid: bool, right: bool) {
        self.left_btn.set_pressed(ctx, left);
        self.middle_btn.set_pressed(ctx, mid);
        self.right_btn.set_pressed(ctx, right);
    }

    /// Handle middle button hold-to-confirm start.
    /// We need to cancel possible holds in both other buttons.
    fn middle_hold_started(&mut self, ctx: &mut EventCtx) {
        self.left_btn.hold_ended(ctx);
        self.middle_btn.hold_started(ctx);
        self.right_btn.hold_ended(ctx);
    }

    /// Handling the HTC elements.
    /// Finding out if they have been triggered and sending event
    /// for the appropriate button.
    /// Setting the state to wait for the appropriate release event
    /// from the pressed button. Also resetting visible state.
    fn handle_hold_to_confirms(
        &mut self,
        ctx: &mut EventCtx,
        event: Event,
    ) -> Option<ButtonControllerMsg> {
        if self.left_btn.htc_got_triggered(ctx, event) {
            self.state = ButtonState::HTCNeedsRelease(PhysicalButton::Left);
            self.set_pressed(ctx, false, false, false);
            return Some(ButtonControllerMsg::Triggered(ButtonPos::Left));
        } else if self.middle_btn.htc_got_triggered(ctx, event) {
            // TODO: how to handle it here? Do we even need to?
            self.state = ButtonState::Nothing;
            self.set_pressed(ctx, false, false, false);
            return Some(ButtonControllerMsg::Triggered(ButtonPos::Middle));
        } else if self.right_btn.htc_got_triggered(ctx, event) {
            self.state = ButtonState::HTCNeedsRelease(PhysicalButton::Right);
            self.set_pressed(ctx, false, false, false);
            return Some(ButtonControllerMsg::Triggered(ButtonPos::Right));
        }
        None
    }
}

impl<T: Clone + AsRef<str>> Component for ButtonController<T> {
    type Msg = ButtonControllerMsg;

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        // State machine for the ButtonController
        // We are matching event with `Event::Button` for a button action
        // and `Event::Timer` for getting the expiration of HTC.
        match event {
            Event::Button(button) => {
                let (new_state, event) = match self.state {
                    ButtonState::Nothing => match button {
                        ButtonEvent::ButtonPressed(which) => {
                            match which {
                                PhysicalButton::Left => {
                                    self.left_btn.hold_started(ctx);
                                }
                                PhysicalButton::Right => {
                                    self.right_btn.hold_started(ctx);
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
                                    self.left_btn.hold_ended(ctx);
                                    None
                                },
                            ),
                            PhysicalButton::Right => (
                                ButtonState::Nothing,
                                if self.right_btn.reacts_to_single_click() {
                                    Some(ButtonControllerMsg::Triggered(ButtonPos::Right))
                                } else {
                                    self.right_btn.hold_ended(ctx);
                                    None
                                },
                            ),
                            _ => (ButtonState::Nothing, None),
                        },

                        ButtonEvent::ButtonPressed(b) if b != which_down => {
                            self.middle_hold_started(ctx);
                            (ButtonState::BothDown, None)
                        }
                        _ => (self.state, None),
                    },
                    ButtonState::BothDown => match button {
                        ButtonEvent::ButtonReleased(b) => {
                            self.middle_btn.hold_ended(ctx);
                            (ButtonState::OneReleased(b), None)
                        }
                        _ => (self.state, None),
                    },
                    ButtonState::OneReleased(which_up) => match button {
                        ButtonEvent::ButtonPressed(b) if b == which_up => {
                            self.middle_hold_started(ctx);
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
                    ButtonState::HTCNeedsRelease(needs_release) => match button {
                        // Only going out of this state if correct button was released
                        ButtonEvent::ButtonReleased(released) if needs_release == released => {
                            (ButtonState::Nothing, None)
                        }
                        _ => (self.state, None),
                    },
                };

                // Updating the visual feedback for the buttons
                match new_state {
                    // Not showing anything also when we wait for a release
                    ButtonState::Nothing | ButtonState::HTCNeedsRelease(_) => {
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
            Event::Timer(_) => self.handle_hold_to_confirms(ctx, event),
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

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for ButtonContainer<T>
where
    T: AsRef<str>,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.open("ButtonContainer");

        // Putting together text representation of the button
        let mut btn_text: String<30> = String::new();
        if let Some(btn) = &self.button {
            match btn.inner().content() {
                ButtonContent::Text(text) => {
                    unwrap!(btn_text.push_str(text.as_ref()));
                }
                ButtonContent::Icon(icon) => {
                    unwrap!(btn_text.push_str("Icon:"));
                    unwrap!(btn_text.push_str(icon.text));
                }
            }
        } else if let Some(htc) = &self.hold_to_confirm {
            unwrap!(btn_text.push_str(htc.inner().get_text().as_ref()));
            unwrap!(btn_text.push_str(" (HTC:"));
            unwrap!(btn_text.push_str(inttostr!(htc.inner().get_duration().to_millis())));
            unwrap!(btn_text.push_str(")"));
        } else {
            unwrap!(btn_text.push_str(crate::trace::EMPTY_BTN));
        }
        t.button(btn_text.as_ref());

        t.close();
    }
}

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for ButtonController<T>
where
    T: AsRef<str>,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.open("ButtonController");
        t.field("left_btn", &self.left_btn);
        t.field("middle_btn", &self.middle_btn);
        t.field("right_btn", &self.right_btn);
        t.close();
    }
}

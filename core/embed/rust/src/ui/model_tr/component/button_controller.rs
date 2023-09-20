use super::{
    theme, Button, ButtonDetails, ButtonLayout, ButtonPos, HoldToConfirm, HoldToConfirmMsg,
};
use crate::{
    strutil::StringType,
    time::{Duration, Instant},
    ui::{
        component::{base::Event, Component, EventCtx, Pad, TimerToken},
        event::{ButtonEvent, PhysicalButton},
        geometry::Rect,
    },
};

/// All possible states buttons (left and right) can be at.
#[derive(Copy, Clone, PartialEq, Eq)]
enum ButtonState {
    /// Both buttons are in untouched state.
    /// _ _
    /// NEXT: OneDown
    Nothing,
    /// One Button is down when previously nothing was.
    /// _ _  ... ↓ _ | _ ↓
    /// NEXT: Nothing, BothDown, HTCNeedsRelease
    OneDown(PhysicalButton),
    /// Both buttons are down ("middle-click").
    /// ↓ _ | _ ↓ ... ↓ ↓
    /// NEXT: OneReleased
    BothDown,
    /// One button is down when previously both were.
    /// Happens when "middle-click" is performed.
    /// ↓ ↓ ... ↓ _ | _ ↓
    /// NEXT: Nothing, BothDown
    OneReleased(PhysicalButton),
    /// One button is down after it triggered a HoldToConfirm event.
    /// Needed so that we can cleanly reset the state.
    /// ↓ _ | _ ↓ ... ↓ _ | _ ↓
    /// NEXT: Nothing
    HTCNeedsRelease(PhysicalButton),
}

pub enum ButtonControllerMsg {
    /// Button was pressed down.
    Pressed(ButtonPos),
    /// Which button was triggered, and whether it was pressed for a longer
    /// time before releasing.
    Triggered(ButtonPos, bool),
    /// Button was pressed and held for longer time (not released yet).
    LongPressed(ButtonPos),
}

/// Defines what kind of button should be currently used.
pub enum ButtonType<T>
where
    T: StringType,
{
    Button(Button<T>),
    HoldToConfirm(HoldToConfirm<T>),
    Nothing,
}

impl<T> ButtonType<T>
where
    T: StringType,
{
    pub fn from_button_details(pos: ButtonPos, btn_details: Option<ButtonDetails<T>>) -> Self {
        if let Some(btn_details) = btn_details {
            if btn_details.duration.is_some() {
                Self::HoldToConfirm(HoldToConfirm::from_button_details(pos, btn_details))
            } else {
                Self::Button(Button::from_button_details(pos, btn_details))
            }
        } else {
            Self::Nothing
        }
    }

    pub fn place(&mut self, button_area: Rect) {
        match self {
            Self::Button(button) => {
                button.place(button_area);
            }
            Self::HoldToConfirm(htc) => {
                htc.place(button_area);
            }
            Self::Nothing => {}
        }
    }

    pub fn paint(&mut self) {
        match self {
            Self::Button(button) => {
                button.paint();
            }
            Self::HoldToConfirm(htc) => {
                htc.paint();
            }
            Self::Nothing => {}
        }
    }
}

/// Wrapping a button and its state, so that it can be easily
/// controlled from outside.
///
/// Users have a choice of a normal button or Hold-to-confirm button.
/// `button_type` specified what from those two is used, if anything.
pub struct ButtonContainer<T>
where
    T: StringType,
{
    pos: ButtonPos,
    button_type: ButtonType<T>,
    /// Holds the timestamp of when the button was pressed.
    pressed_since: Option<Instant>,
    /// How long the button should be pressed to send `long_press=true` in
    /// `ButtonControllerMsg::Triggered`
    long_press_ms: u32,
    /// Timer for sending `ButtonControllerMsg::LongPressed`
    long_pressed_timer: Option<TimerToken>,
    /// Whether it should even send `ButtonControllerMsg::LongPressed` events
    /// (optional)
    send_long_press: bool,
}

impl<T> ButtonContainer<T>
where
    T: StringType,
{
    /// Supplying `None` as `btn_details`  marks the button inactive
    /// (it can be later activated in `set()`).
    pub fn new(pos: ButtonPos, btn_details: Option<ButtonDetails<T>>) -> Self {
        const DEFAULT_LONG_PRESS_MS: u32 = 1000;
        let send_long_press = btn_details
            .as_ref()
            .map_or(false, |btn| btn.send_long_press);
        Self {
            pos,
            button_type: ButtonType::from_button_details(pos, btn_details),
            pressed_since: None,
            long_press_ms: DEFAULT_LONG_PRESS_MS,
            long_pressed_timer: None,
            send_long_press,
        }
    }

    /// Changing the state of the button.
    ///
    /// Passing `None` as `btn_details` will mark the button as inactive.
    pub fn set(&mut self, btn_details: Option<ButtonDetails<T>>, button_area: Rect) {
        self.send_long_press = btn_details
            .as_ref()
            .map_or(false, |btn| btn.send_long_press);
        self.button_type = ButtonType::from_button_details(self.pos, btn_details);
        self.button_type.place(button_area);
    }

    /// Placing the possible component.
    pub fn place(&mut self, bounds: Rect) {
        self.button_type.place(bounds);
    }

    /// Painting the component that should be currently visible, if any.
    pub fn paint(&mut self) {
        self.button_type.paint();
    }

    /// Setting the visual state of the button - released/pressed.
    pub fn set_pressed(&mut self, ctx: &mut EventCtx, is_pressed: bool) {
        if let ButtonType::Button(btn) = &mut self.button_type {
            btn.set_pressed(ctx, is_pressed);
        }
    }

    /// Trigger an action or end hold.
    /// Called when the button is released. If it is a simple button, it returns
    /// a Triggered message. If it is a hold-to-confirm button, it ends the
    /// hold.
    pub fn maybe_trigger(&mut self, ctx: &mut EventCtx) -> Option<ButtonControllerMsg> {
        match self.button_type {
            ButtonType::Button(_) => {
                // Finding out whether the button was long-pressed
                let long_press = self.pressed_since.map_or(false, |since| {
                    Instant::now().saturating_duration_since(since).to_millis() > self.long_press_ms
                });
                self.pressed_since = None;
                self.long_pressed_timer = None;
                Some(ButtonControllerMsg::Triggered(self.pos, long_press))
            }
            _ => {
                self.hold_ended(ctx);
                None
            }
        }
    }

    /// Find out whether hold-to-confirm was triggered.
    pub fn htc_got_triggered(&mut self, ctx: &mut EventCtx, event: Event) -> bool {
        if let ButtonType::HoldToConfirm(htc) = &mut self.button_type {
            if matches!(htc.event(ctx, event), Some(HoldToConfirmMsg::Confirmed)) {
                return true;
            }
        }
        false
    }

    /// Saving the timestamp of when the button was pressed.
    /// Also requesting a timer for long-press if wanted.
    pub fn got_pressed(&mut self, ctx: &mut EventCtx) {
        self.pressed_since = Some(Instant::now());
        if self.send_long_press {
            self.long_pressed_timer =
                Some(ctx.request_timer(Duration::from_millis(self.long_press_ms)));
        }
    }

    /// Reset the pressed information.
    pub fn reset(&mut self) {
        self.pressed_since = None;
        self.long_pressed_timer = None;
    }

    /// Whether token matches what we have
    pub fn is_timer_token(&self, token: TimerToken) -> bool {
        self.long_pressed_timer == Some(token)
    }

    /// Registering hold event.
    pub fn hold_started(&mut self, ctx: &mut EventCtx) {
        if let ButtonType::HoldToConfirm(htc) = &mut self.button_type {
            htc.event(ctx, Event::Button(ButtonEvent::HoldStarted));
        }
    }

    /// Cancelling hold event.
    pub fn hold_ended(&mut self, ctx: &mut EventCtx) {
        if let ButtonType::HoldToConfirm(htc) = &mut self.button_type {
            htc.event(ctx, Event::Button(ButtonEvent::HoldEnded));
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
///
/// There is optional complexity with IgnoreButtonDelay, which gets executed
/// only in cases where clients request it.
pub struct ButtonController<T>
where
    T: StringType,
{
    pad: Pad,
    left_btn: ButtonContainer<T>,
    middle_btn: ButtonContainer<T>,
    right_btn: ButtonContainer<T>,
    state: ButtonState,
    /// Button area is needed so the buttons
    /// can be "re-placed" after their text is changed
    /// Will be set in `place`
    button_area: Rect,
    /// Handling optional ignoring of buttons after pressing the other button.
    ignore_btn_delay: Option<IgnoreButtonDelay>,
}

impl<T> ButtonController<T>
where
    T: StringType,
{
    pub fn new(btn_layout: ButtonLayout<T>) -> Self {
        Self {
            pad: Pad::with_background(theme::BG).with_clear(),
            left_btn: ButtonContainer::new(ButtonPos::Left, btn_layout.btn_left),
            middle_btn: ButtonContainer::new(ButtonPos::Middle, btn_layout.btn_middle),
            right_btn: ButtonContainer::new(ButtonPos::Right, btn_layout.btn_right),
            state: ButtonState::Nothing,
            button_area: Rect::zero(),
            ignore_btn_delay: None,
        }
    }

    /// Set up the logic to ignore a button after some time from pressing
    /// the other button.
    pub fn with_ignore_btn_delay(mut self, delay_ms: u32) -> Self {
        self.ignore_btn_delay = Some(IgnoreButtonDelay::new(delay_ms));
        self
    }

    /// Updating all the three buttons to the wanted states.
    pub fn set(&mut self, btn_layout: ButtonLayout<T>) {
        self.pad.clear();
        self.left_btn.set(btn_layout.btn_left, self.button_area);
        self.middle_btn.set(btn_layout.btn_middle, self.button_area);
        self.right_btn.set(btn_layout.btn_right, self.button_area);
    }

    /// Setting the pressed state for all three buttons by boolean flags.
    fn set_pressed(&mut self, ctx: &mut EventCtx, left: bool, mid: bool, right: bool) {
        self.left_btn.set_pressed(ctx, left);
        self.middle_btn.set_pressed(ctx, mid);
        self.right_btn.set_pressed(ctx, right);
    }

    pub fn highlight_button(&mut self, ctx: &mut EventCtx, pos: ButtonPos) {
        match pos {
            ButtonPos::Left => self.left_btn.set_pressed(ctx, true),
            ButtonPos::Middle => self.middle_btn.set_pressed(ctx, true),
            ButtonPos::Right => self.right_btn.set_pressed(ctx, true),
        }
    }

    /// Handle middle button hold-to-confirm start.
    /// We need to cancel possible holds in both other buttons.
    fn middle_hold_started(&mut self, ctx: &mut EventCtx) {
        self.left_btn.hold_ended(ctx);
        self.middle_btn.hold_started(ctx);
        self.right_btn.hold_ended(ctx);
    }

    /// Handling the expiration of HTC elements.
    /// Finding out if they have been triggered and sending event
    /// for the appropriate button.
    /// Setting the state to wait for the appropriate release event
    /// from the pressed button. Also resetting visible state.
    fn handle_htc_expiration(
        &mut self,
        ctx: &mut EventCtx,
        event: Event,
    ) -> Option<ButtonControllerMsg> {
        if self.left_btn.htc_got_triggered(ctx, event) {
            self.state = ButtonState::HTCNeedsRelease(PhysicalButton::Left);
            self.set_pressed(ctx, false, false, false);
            return Some(ButtonControllerMsg::Triggered(ButtonPos::Left, true));
        } else if self.middle_btn.htc_got_triggered(ctx, event) {
            self.state = ButtonState::Nothing;
            self.set_pressed(ctx, false, false, false);
            return Some(ButtonControllerMsg::Triggered(ButtonPos::Middle, true));
        } else if self.right_btn.htc_got_triggered(ctx, event) {
            self.state = ButtonState::HTCNeedsRelease(PhysicalButton::Right);
            self.set_pressed(ctx, false, false, false);
            return Some(ButtonControllerMsg::Triggered(ButtonPos::Right, true));
        }
        None
    }

    fn reset_button_presses(&mut self) {
        self.left_btn.reset();
        self.middle_btn.reset();
        self.right_btn.reset();
    }

    fn got_pressed(&mut self, ctx: &mut EventCtx, pos: ButtonPos) {
        // Only one (virtual) button can be pressed at the same time
        self.reset_button_presses();
        match pos {
            ButtonPos::Left => {
                self.left_btn.got_pressed(ctx);
            }
            ButtonPos::Middle => {
                self.middle_btn.got_pressed(ctx);
            }
            ButtonPos::Right => {
                self.right_btn.got_pressed(ctx);
            }
        }
    }

    fn handle_long_press_timer_token(&mut self, token: TimerToken) -> Option<ButtonPos> {
        if self.left_btn.is_timer_token(token) {
            return Some(ButtonPos::Left);
        }
        if self.middle_btn.is_timer_token(token) {
            return Some(ButtonPos::Middle);
        }
        if self.right_btn.is_timer_token(token) {
            return Some(ButtonPos::Right);
        }
        None
    }

    /// Resetting the state of the controller.
    pub fn reset_state(&mut self, ctx: &mut EventCtx) {
        self.state = ButtonState::Nothing;
        self.reset_button_presses();
        self.set_pressed(ctx, false, false, false);
        if let Some(ignore_btn_delay) = &mut self.ignore_btn_delay {
            ignore_btn_delay.reset();
        }
    }
}

impl<T> Component for ButtonController<T>
where
    T: StringType,
{
    type Msg = ButtonControllerMsg;

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        // State machine for the ButtonController
        // We are matching event with `Event::Button` for a button action
        // and `Event::Timer` for getting the expiration of HTC.
        match event {
            Event::Button(button_event) => {
                let (new_state, event) = match self.state {
                    // _ _
                    ButtonState::Nothing => match button_event {
                        // ▼ * | * ▼
                        ButtonEvent::ButtonPressed(which) => {
                            // ↓ _ | _ ↓
                            // Initial button press will set the timer for second button,
                            // and after some delay, it will become un-clickable
                            if let Some(ignore_btn_delay) = &mut self.ignore_btn_delay {
                                ignore_btn_delay.handle_button_press(ctx, which);
                            }
                            (
                                ButtonState::OneDown(which),
                                match which {
                                    // ▼ *
                                    PhysicalButton::Left => {
                                        self.got_pressed(ctx, ButtonPos::Left);
                                        self.left_btn.hold_started(ctx);
                                        Some(ButtonControllerMsg::Pressed(ButtonPos::Left))
                                    }
                                    // * ▼
                                    PhysicalButton::Right => {
                                        self.got_pressed(ctx, ButtonPos::Right);
                                        self.right_btn.hold_started(ctx);
                                        Some(ButtonControllerMsg::Pressed(ButtonPos::Right))
                                    }
                                },
                            )
                        }
                        _ => (self.state, None),
                    },
                    // ↓ _ | _ ↓
                    ButtonState::OneDown(which_down) => match button_event {
                        // ▲ * | * ▲
                        ButtonEvent::ButtonReleased(b) if b == which_down => match which_down {
                            // ▲ *
                            // Trigger the button and make the second one clickable in all cases
                            PhysicalButton::Left => {
                                if let Some(ignore_btn_delay) = &mut self.ignore_btn_delay {
                                    ignore_btn_delay.make_button_clickable(ButtonPos::Right);
                                }
                                // _ _
                                (ButtonState::Nothing, self.left_btn.maybe_trigger(ctx))
                            }
                            // * ▲
                            PhysicalButton::Right => {
                                if let Some(ignore_btn_delay) = &mut self.ignore_btn_delay {
                                    ignore_btn_delay.make_button_clickable(ButtonPos::Left);
                                }
                                // _ _
                                (ButtonState::Nothing, self.right_btn.maybe_trigger(ctx))
                            }
                        },
                        // * ▼ | ▼ *
                        ButtonEvent::ButtonPressed(b) if b != which_down => {
                            // Buttons may be non-clickable (caused by long-holding the other
                            // button)
                            if let Some(ignore_btn_delay) = &self.ignore_btn_delay {
                                if ignore_btn_delay.ignore_button(b) {
                                    return None;
                                }
                            }
                            self.got_pressed(ctx, ButtonPos::Middle);
                            self.middle_hold_started(ctx);
                            (
                                // ↓ ↓
                                ButtonState::BothDown,
                                Some(ButtonControllerMsg::Pressed(ButtonPos::Middle)),
                            )
                        }
                        _ => (self.state, None),
                    },
                    // ↓ ↓
                    ButtonState::BothDown => match button_event {
                        // ▲ * | * ▲
                        ButtonEvent::ButtonReleased(b) => {
                            self.middle_btn.hold_ended(ctx);
                            // _ ↓ | ↓ _
                            (ButtonState::OneReleased(b), None)
                        }
                        _ => (self.state, None),
                    },
                    // ↓ _ | _ ↓
                    ButtonState::OneReleased(which_up) => match button_event {
                        // * ▼ | ▼ *
                        ButtonEvent::ButtonPressed(b) if b == which_up => {
                            self.middle_hold_started(ctx);
                            // ↓ ↓
                            (ButtonState::BothDown, None)
                        }
                        // ▲ * | * ▲
                        ButtonEvent::ButtonReleased(b) if b != which_up => {
                            // _ _
                            // Both buttons need to be clickable now
                            if let Some(ignore_btn_delay) = &mut self.ignore_btn_delay {
                                ignore_btn_delay.make_button_clickable(ButtonPos::Left);
                                ignore_btn_delay.make_button_clickable(ButtonPos::Right);
                            }
                            (ButtonState::Nothing, self.middle_btn.maybe_trigger(ctx))
                        }
                        _ => (self.state, None),
                    },
                    // ↓ _ | _ ↓
                    ButtonState::HTCNeedsRelease(needs_release) => match button_event {
                        // Only going out of this state if correct button was released
                        // ▲ * | * ▲
                        ButtonEvent::ButtonReleased(released) if needs_release == released => {
                            // _ _
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
                    },
                    ButtonState::BothDown | ButtonState::OneReleased(_) => {
                        self.set_pressed(ctx, false, true, false);
                    }
                };

                self.state = new_state;
                event
            }
            // Timer - handle clickable properties and HoldToConfirm expiration
            Event::Timer(token) => {
                if let Some(ignore_btn_delay) = &mut self.ignore_btn_delay {
                    ignore_btn_delay.handle_timer_token(token);
                }
                if let Some(pos) = self.handle_long_press_timer_token(token) {
                    return Some(ButtonControllerMsg::LongPressed(pos));
                }
                self.handle_htc_expiration(ctx, event)
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

/// When one button is pressed, the other one becomes un-clickable after some
/// small time period. This is to prevent accidental clicks when user is holding
/// the button to automatically move through items.
struct IgnoreButtonDelay {
    /// How big is the delay after the button is inactive
    delay: Duration,
    /// Whether left button is currently clickable
    left_clickable: bool,
    /// Whether right button is currently clickable
    right_clickable: bool,
    /// Timer for setting the left_clickable
    left_clickable_timer: Option<TimerToken>,
    /// Timer for setting the right_clickable
    right_clickable_timer: Option<TimerToken>,
}

impl IgnoreButtonDelay {
    pub fn new(delay_ms: u32) -> Self {
        Self {
            delay: Duration::from_millis(delay_ms),
            left_clickable: true,
            right_clickable: true,
            left_clickable_timer: None,
            right_clickable_timer: None,
        }
    }

    pub fn make_button_clickable(&mut self, pos: ButtonPos) {
        match pos {
            ButtonPos::Left => {
                self.left_clickable = true;
                self.left_clickable_timer = None;
            }
            ButtonPos::Right => {
                self.right_clickable = true;
                self.right_clickable_timer = None;
            }
            ButtonPos::Middle => {}
        }
    }

    pub fn handle_button_press(&mut self, ctx: &mut EventCtx, button: PhysicalButton) {
        if matches!(button, PhysicalButton::Left) {
            self.right_clickable_timer = Some(ctx.request_timer(self.delay));
        }
        if matches!(button, PhysicalButton::Right) {
            self.left_clickable_timer = Some(ctx.request_timer(self.delay));
        }
    }

    pub fn ignore_button(&self, button: PhysicalButton) -> bool {
        if matches!(button, PhysicalButton::Left) && !self.left_clickable {
            return true;
        }
        if matches!(button, PhysicalButton::Right) && !self.right_clickable {
            return true;
        }
        false
    }

    pub fn handle_timer_token(&mut self, token: TimerToken) {
        if self.left_clickable_timer == Some(token) {
            self.left_clickable = false;
            self.left_clickable_timer = None;
        }
        if self.right_clickable_timer == Some(token) {
            self.right_clickable = false;
            self.right_clickable_timer = None;
        }
    }

    pub fn reset(&mut self) {
        self.left_clickable = true;
        self.right_clickable = true;
        self.left_clickable_timer = None;
        self.right_clickable_timer = None;
    }
}

/// Component allowing for automatically moving through items (e.g. Choice
/// items).
///
/// Users are in full control of starting/stopping the movement.
///
/// Can be started e.g. by holding left/right button.
pub struct AutomaticMover {
    /// For requesting timer events repeatedly
    timer_token: Option<TimerToken>,
    /// Which direction should we go (which button is down)
    moving_direction: Option<ButtonPos>,
    /// How many screens were moved automatically
    auto_moved_screens: usize,
    /// Function to get duration of each movement according to the already moved
    /// steps
    duration_func: fn(usize) -> u32,
}

impl AutomaticMover {
    pub fn new() -> Self {
        fn default_duration_func(steps: usize) -> u32 {
            match steps {
                x if x < 3 => 200,
                x if x < 10 => 150,
                _ => 100,
            }
        }

        Self {
            timer_token: None,
            moving_direction: None,
            auto_moved_screens: 0,
            duration_func: default_duration_func,
        }
    }

    pub fn with_duration_func(mut self, duration_func: fn(usize) -> u32) -> Self {
        self.duration_func = duration_func;
        self
    }

    /// Determines how long to wait between automatic movements.
    /// Moves quicker with increasing number of screens moved.
    /// Can be forced to be always the same (e.g. for animation purposes).
    fn get_auto_move_duration(&self) -> Duration {
        // Calculating duration from function
        let ms_duration = (self.duration_func)(self.auto_moved_screens);
        Duration::from_millis(ms_duration)
    }

    /// In which direction we are moving, if any
    pub fn moving_direction(&self) -> Option<ButtonPos> {
        self.moving_direction
    }

    // Whether we are currently moving.
    pub fn is_moving(&self) -> bool {
        self.moving_direction.is_some()
    }

    /// Whether we have done at least one automatic movement.
    pub fn was_moving(&self) -> bool {
        self.auto_moved_screens > 0
    }

    pub fn start_moving(&mut self, ctx: &mut EventCtx, button: ButtonPos) {
        self.auto_moved_screens = 0;
        self.moving_direction = Some(button);
        self.timer_token = Some(ctx.request_timer(self.get_auto_move_duration()));
    }

    pub fn stop_moving(&mut self) {
        self.moving_direction = None;
        self.timer_token = None;
    }
}

impl Component for AutomaticMover {
    type Msg = ButtonPos;

    fn place(&mut self, bounds: Rect) -> Rect {
        bounds
    }

    fn paint(&mut self) {}

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        // Moving automatically only when we receive a TimerToken that we have
        // requested before
        if let Event::Timer(token) = event {
            if self.timer_token == Some(token) && self.moving_direction.is_some() {
                // Request new token and send the appropriate button trigger event
                self.timer_token = Some(ctx.request_timer(self.get_auto_move_duration()));
                self.auto_moved_screens += 1;
                return self.moving_direction;
            }
        }
        None
    }
}

// DEBUG-ONLY SECTION BELOW

#[cfg(feature = "ui_debug")]
impl<T: StringType> crate::trace::Trace for ButtonContainer<T> {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        if let ButtonType::Button(btn) = &self.button_type {
            btn.trace(t);
        } else if let ButtonType::HoldToConfirm(htc) = &self.button_type {
            htc.trace(t);
        }
    }
}

#[cfg(feature = "ui_debug")]
impl<T: StringType> crate::trace::Trace for ButtonController<T> {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("ButtonController");
        t.child("left_btn", &self.left_btn);
        t.child("middle_btn", &self.middle_btn);
        t.child("right_btn", &self.right_btn);
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for AutomaticMover {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("AutomaticMover");
    }
}

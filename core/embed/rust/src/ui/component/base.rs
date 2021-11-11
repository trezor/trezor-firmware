use core::{mem, time::Duration};

use heapless::Vec;

#[cfg(feature = "model_t1")]
use crate::ui::model_t1::event::ButtonEvent;
#[cfg(feature = "model_tt")]
use crate::ui::model_tt::event::TouchEvent;

/// Type used by components that do not return any messages.
///
/// Alternative to the yet-unstable `!`-type.
pub enum Never {}

pub trait Component {
    type Msg;
    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg>;
    fn paint(&mut self);
}

pub struct Child<T> {
    component: T,
    marked_for_paint: bool,
}

impl<T> Child<T> {
    pub fn new(component: T) -> Self {
        Self {
            component,
            marked_for_paint: true,
        }
    }

    pub fn inner(&self) -> &T {
        &self.component
    }

    pub fn into_inner(self) -> T {
        self.component
    }

    pub fn mutate<F, U>(&mut self, ctx: &mut EventCtx, component_func: F) -> U
    where
        F: FnOnce(&mut EventCtx, &mut T) -> U,
    {
        let paint_was_previously_requested = mem::replace(&mut ctx.paint_requested, false);
        let component_result = component_func(ctx, &mut self.component);
        if ctx.paint_requested {
            self.marked_for_paint = true;
        } else {
            ctx.paint_requested = paint_was_previously_requested;
        }
        component_result
    }
}

impl<T> Component for Child<T>
where
    T: Component,
{
    type Msg = T::Msg;

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.mutate(ctx, |ctx, c| c.event(ctx, event))
    }

    fn paint(&mut self) {
        if self.marked_for_paint {
            self.marked_for_paint = false;
            self.component.paint();
        }
    }
}

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for Child<T>
where
    T: crate::trace::Trace,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        self.component.trace(t)
    }
}

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum Event {
    #[cfg(feature = "model_t1")]
    Button(ButtonEvent),
    #[cfg(feature = "model_tt")]
    Touch(TouchEvent),
    Timer(TimerToken),
}

#[derive(Copy, Clone, PartialEq, Eq)]
pub struct TimerToken(usize);

impl TimerToken {
    /// Value of an invalid (or missing) token.
    pub const INVALID: TimerToken = TimerToken(0);

    pub fn from_raw(raw: usize) -> Self {
        Self(raw)
    }

    pub fn into_raw(self) -> usize {
        self.0
    }
}

pub struct EventCtx {
    timers: Vec<(TimerToken, Duration), { Self::MAX_TIMERS }>,
    next_token: usize,
    paint_requested: bool,
}

impl EventCtx {
    /// Maximum amount of timers requested in one event tick.
    const MAX_TIMERS: usize = 4;

    pub fn new() -> Self {
        Self {
            timers: Vec::new(),
            next_token: 1,
            paint_requested: false,
        }
    }

    pub fn request_paint(&mut self) {
        self.paint_requested = true;
    }

    pub fn clear_paint_requests(&mut self) {
        self.paint_requested = false;
    }

    pub fn request_timer(&mut self, deadline: Duration) -> TimerToken {
        let token = self.next_timer_token();
        if self.timers.push((token, deadline)).is_err() {
            // The timer queue is full. Let's just ignore this request.
            #[cfg(feature = "ui_debug")]
            panic!("Timer queue is full");
        }
        token
    }

    pub fn pop_timer(&mut self) -> Option<(TimerToken, Duration)> {
        self.timers.pop()
    }

    fn next_timer_token(&mut self) -> TimerToken {
        let token = TimerToken(self.next_token);
        self.next_token += 1;
        token
    }
}

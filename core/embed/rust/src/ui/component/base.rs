use core::mem;

use heapless::Vec;

use crate::{time::Duration, ui::geometry::Point};

/// Type used by components that do not return any messages.
///
/// Alternative to the yet-unstable `!`-type.
pub enum Never {}

/// User interface is composed of components that can react to `Event`s through
/// the `event` method and know how to paint themselves to screen through the
/// `paint` method.  Components can emit messages as a reaction to events.
pub trait Component {
    type Msg;
    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg>;
    fn paint(&mut self);
}

/// Components should always avoid unnecessary overpaint to prevent obvious
/// tearing and flickering. `Child` wraps an inner component `T` and keeps a
/// dirty flag for it. Any mutation of `T` has to happen through the `mutate`
/// accessor, `T` can then request a paint call to be scheduled later by calling
/// `EventCtx::request_paint` in its `event` pass.
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

    /// Access inner component mutably, track whether a paint call has been
    /// requested, and propagate the flag upwards the component tree.
    pub fn mutate<F, U>(&mut self, ctx: &mut EventCtx, component_func: F) -> U
    where
        F: FnOnce(&mut EventCtx, &mut T) -> U,
    {
        let prev_requested = mem::replace(&mut ctx.paint_requested, false);
        let result = component_func(ctx, &mut self.component);
        if ctx.paint_requested {
            // If a paint was requested anywhere in the inner component tree, we need to
            // mark ourselves for paint as well, and keep the `ctx` flag so it can
            // propagate upwards.
            self.marked_for_paint = true;
        } else {
            // Paint has not been requested in the *inner* component, so there's no need to
            // paint it, but we need to preserve the previous flag carried in `ctx` so it
            // properly propagates upwards (i.e. from our previous siblings).
            ctx.paint_requested = prev_requested;
        }
        result
    }
}

impl<T> Component for Child<T>
where
    T: Component,
{
    type Msg = T::Msg;

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.mutate(ctx, |ctx, c| {
            // Handle the internal invalidation event here, so components don't have to. We
            // still pass it inside, so the event propagates correctly to all components in
            // the sub-tree.
            if let Event::RequestPaint = event {
                ctx.request_paint();
            }
            c.event(ctx, event)
        })
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

pub trait ComponentExt: Sized {
    fn into_child(self) -> Child<Self>;
}

impl<T> ComponentExt for T
where
    T: Component,
{
    fn into_child(self) -> Child<Self> {
        Child::new(self)
    }
}

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum Event {
    /// A person has started touching the screen at given absolute coordinates.
    /// `TouchMove` will usually follow, and `TouchEnd` should finish the
    /// interaction.
    TouchStart(Point),
    /// Touch has moved into a different point on the screen.
    TouchMove(Point),
    /// Touch has ended at a point on the screen.
    TouchEnd(Point),
    /// Previously requested timer was triggered. This invalidates the timer
    /// token (another timer has to be requested).
    Timer(TimerToken),
    /// Internally-handled event to inform all `Child` wrappers in a sub-tree to
    /// get scheduled for painting.
    RequestPaint,
}

#[derive(Copy, Clone, PartialEq, Eq)]
pub struct TimerToken(u32);

impl TimerToken {
    /// Value of an invalid (or missing) token.
    pub const INVALID: TimerToken = TimerToken(0);

    pub const fn from_raw(raw: u32) -> Self {
        Self(raw)
    }

    pub const fn into_raw(self) -> u32 {
        self.0
    }
}

pub struct EventCtx {
    timers: Vec<(TimerToken, Duration), { Self::MAX_TIMERS }>,
    next_token: u32,
    paint_requested: bool,
}

impl EventCtx {
    /// Timer token dedicated for animation frames.
    pub const ANIM_FRAME_TIMER: TimerToken = TimerToken(1);

    // 0 == `TimerToken::INVALID`,
    // 1 == `Self::ANIM_FRAME_TIMER`.
    const STARTING_TIMER_TOKEN: u32 = 2;

    /// Maximum amount of timers requested in one event tick.
    const MAX_TIMERS: usize = 4;

    pub fn new() -> Self {
        Self {
            timers: Vec::new(),
            next_token: Self::STARTING_TIMER_TOKEN,
            paint_requested: false,
        }
    }

    /// Indicate that the inner state of the component has changed, any screen
    /// content it has painted before is now invalid, and it should be painted
    /// again by the nearest `Child` wrapper.
    pub fn request_paint(&mut self) {
        self.paint_requested = true;
    }

    pub fn clear_paint_requests(&mut self) {
        self.paint_requested = false;
    }

    /// Request a timer event to be delivered after `deadline` elapses.
    pub fn request_timer(&mut self, deadline: Duration) -> TimerToken {
        let token = self.next_timer_token();
        self.register_timer(token, deadline);
        token
    }

    /// Request an animation frame timer to fire as soon as possible.
    pub fn request_anim_frame(&mut self) {
        self.register_timer(Self::ANIM_FRAME_TIMER, Duration::ZERO);
    }

    pub fn pop_timer(&mut self) -> Option<(TimerToken, Duration)> {
        self.timers.pop()
    }

    fn register_timer(&mut self, token: TimerToken, deadline: Duration) {
        if self.timers.push((token, deadline)).is_err() {
            // The timer queue is full, this would be a development error in the layout
            // layer. Let's panic in the debug env.
            #[cfg(feature = "ui_debug")]
            panic!("timer queue is full");
        }
    }

    fn next_timer_token(&mut self) -> TimerToken {
        let token = TimerToken(self.next_token);
        // We start again from the beginning if the token counter overflows. This would
        // probably happen in case of a bug and a long-running session. Let's risk the
        // collisions in such case.
        self.next_token = self
            .next_token
            .checked_add(1)
            .unwrap_or(Self::STARTING_TIMER_TOKEN);
        token
    }
}

//! Time-driven attach animation.
//!
//! A component holds an [`AttachAnim`], feeds it every event and reads its
//! progress in `render()`. The animation is armed by `Event::Attach` and
//! carries the direction of the attach.
//!
//! Direction convention: the direction of motion. `AttachType::Swipe(Up)`
//! means the content moves up, i.e. it enters from below. See
//! [`AttachType::motion`].

use easer::functions::Easing;
use sys::time::Duration;

use crate::time::Stopwatch;
use crate::ui::component::base::AttachType;
use crate::ui::component::{Event, EventCtx};
use crate::ui::geometry::{Direction, Offset};
use crate::ui::lerp::Lerp;
use crate::ui::util::animation_disabled;

#[derive(Copy, Clone, PartialEq, Eq)]
enum State {
    /// Not animating, the content is shown in its final state.
    Idle,
    /// Armed by an attach, waiting for the first animation frame. The timer
    /// is started lazily to avoid a jump if the first frame comes late.
    Pending,
    /// Running, the timer measures time since the first animation frame.
    Running,
}

#[derive(Clone)]
pub struct AttachAnim {
    duration: Duration,
    timer: Stopwatch,
    state: State,
    dir: Option<Direction>,
}

impl AttachAnim {
    /// New animation in the finished state; it starts only on attach.
    pub const fn new(duration: Duration) -> Self {
        Self {
            duration,
            timer: Stopwatch::Stopped(Duration::ZERO),
            state: State::Idle,
            dir: None,
        }
    }

    /// Process an event. Starts the animation on `Attach(Initial | Swipe(_))`
    /// and drives it on animation frames. `Attach(Resume)` finishes it.
    ///
    /// Events are never consumed; use `is_active()` to block input.
    pub fn event(&mut self, ctx: &mut EventCtx, event: Event) {
        self.event_filtered(ctx, event, |_| true);
    }

    /// Like `event()`, but `animate` decides whether an attach of the given
    /// type is animated. A non-animated attach finishes the animation.
    pub fn event_filtered(
        &mut self,
        ctx: &mut EventCtx,
        event: Event,
        animate: impl FnOnce(AttachType) -> bool,
    ) {
        match event {
            Event::Attach(AttachType::Resume) => self.finish(),
            Event::Attach(attach) if animate(attach) => self.start(ctx, attach.motion()),
            Event::Attach(_) => self.finish(),
            Event::Timer(EventCtx::ANIM_FRAME_TIMER) => self.anim_frame(ctx),
            _ => {}
        }
    }

    /// Start (or restart) the animation without an attach event, e.g. on an
    /// internal page change.
    pub fn start(&mut self, ctx: &mut EventCtx, dir: Option<Direction>) {
        if animation_disabled() {
            self.finish();
            return;
        }
        self.dir = dir;
        self.timer = Stopwatch::new_stopped();
        self.state = State::Pending;
        ctx.request_anim_frame();
        ctx.request_paint();
    }

    /// Jump to the final state.
    pub fn finish(&mut self) {
        self.state = State::Idle;
    }

    fn anim_frame(&mut self, ctx: &mut EventCtx) {
        match self.state {
            State::Idle => {}
            State::Pending => {
                self.timer.start();
                self.state = State::Running;
                ctx.request_anim_frame();
                ctx.request_paint();
            }
            State::Running if self.timer.is_running_within(self.duration) => {
                ctx.request_anim_frame();
                ctx.request_paint();
            }
            State::Running => {
                // one last paint in the final state
                self.state = State::Idle;
                ctx.request_paint();
            }
        }
    }

    /// Whether the animation is pending or running.
    pub fn is_active(&self) -> bool {
        !animation_disabled() && self.state != State::Idle
    }

    /// Direction of motion of the current attach, `None` if the content
    /// appears in place.
    pub fn dir(&self) -> Option<Direction> {
        self.dir
    }

    /// Progress of the whole animation, `0.0..=1.0`. `1.0` when idle.
    pub fn t(&self) -> f32 {
        self.window(Duration::ZERO, self.duration)
    }

    /// Progress of the interval `start..start + len` within the animation,
    /// `0.0..=1.0`. Used for staggered or delayed parts of an animation.
    pub fn window(&self, start: Duration, len: Duration) -> f32 {
        if animation_disabled() {
            return 1.0;
        }
        match self.state {
            State::Idle => 1.0,
            State::Pending => 0.0,
            State::Running => match self.timer.elapsed().checked_sub(start) {
                None => 0.0,
                Some(_) if len == Duration::ZERO => 1.0,
                Some(elapsed) => (elapsed / len).min(1.0),
            },
        }
    }
}

/// Ease-in of a progress `x` in `0.0..=1.0`.
pub fn ease_in<E: Easing<f32>>(x: f32) -> f32 {
    E::ease_in(x.clamp(0.0, 1.0), 0.0, 1.0, 1.0)
}

/// Ease-out of a progress `x` in `0.0..=1.0`.
pub fn ease_out<E: Easing<f32>>(x: f32) -> f32 {
    E::ease_out(x.clamp(0.0, 1.0), 0.0, 1.0, 1.0)
}

/// Ease-in-out of a progress `x` in `0.0..=1.0`.
pub fn ease_in_out<E: Easing<f32>>(x: f32) -> f32 {
    E::ease_in_out(x.clamp(0.0, 1.0), 0.0, 1.0, 1.0)
}

/// Offset of content moving in direction `dir`, starting `distance` pixels
/// away and arriving at its place at progress `x == 1.0`.
pub fn slide_in(dir: Direction, distance: i16, x: f32) -> Offset {
    let from = -dir.as_offset(Offset::uniform(distance));
    Offset::lerp(from, Offset::zero(), x)
}

/// Opacity of content fading in, `0` at `x == 0.0`, `255` at `x == 1.0`.
pub fn fade_in(x: f32) -> u8 {
    u8::lerp(0, 255, x.clamp(0.0, 1.0))
}

#[cfg(test)]
mod tests {
    use super::*;

    const DURATION: Duration = Duration::from_millis(500);

    #[test]
    fn new_is_finished() {
        let anim = AttachAnim::new(DURATION);
        assert!(!anim.is_active());
        assert_eq!(anim.t(), 1.0);
    }

    #[test]
    fn attach_arms_with_direction() {
        let mut ctx = EventCtx::new();
        let mut anim = AttachAnim::new(DURATION);

        anim.event(&mut ctx, Event::Attach(AttachType::Swipe(Direction::Up)));
        assert!(anim.is_active());
        assert_eq!(anim.t(), 0.0);
        assert!(anim.dir() == Some(Direction::Up));

        anim.event(&mut ctx, Event::Attach(AttachType::Initial));
        assert!(anim.is_active());
        assert!(anim.dir().is_none());
    }

    #[test]
    fn resume_and_filtered_attach_finish() {
        let mut ctx = EventCtx::new();
        let mut anim = AttachAnim::new(DURATION);

        anim.event(&mut ctx, Event::Attach(AttachType::Initial));
        anim.event(&mut ctx, Event::Attach(AttachType::Resume));
        assert!(!anim.is_active());
        assert_eq!(anim.t(), 1.0);

        anim.event(&mut ctx, Event::Attach(AttachType::Initial));
        anim.event_filtered(&mut ctx, Event::Attach(AttachType::Initial), |_| false);
        assert!(!anim.is_active());
    }

    #[test]
    fn slide_in_follows_motion() {
        // moving up = starts below
        assert!(slide_in(Direction::Up, 20, 0.0) == Offset::y(20));
        assert!(slide_in(Direction::Down, 20, 0.0) == Offset::y(-20));
        // moving left = starts on the right
        assert!(slide_in(Direction::Left, 20, 0.0) == Offset::x(20));
        assert!(slide_in(Direction::Right, 20, 0.0) == Offset::x(-20));
        assert!(slide_in(Direction::Up, 20, 1.0) == Offset::zero());
    }
}

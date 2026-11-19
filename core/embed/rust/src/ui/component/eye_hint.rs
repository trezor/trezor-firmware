use sys::time::Duration;

use crate::time::Stopwatch;
use crate::ui::component::{Event, EventCtx, Timer};
use crate::ui::util::animation_disabled;

/// Slide-in of the eye icon hinting that the hidden passphrase can be
/// revealed.
///
/// Once the first hidden character appears, the icon slides in from the left
/// while the hidden characters move right to make room for it.
pub struct EyeHintAnimation {
    /// One-shot timer for the pause before the slide-in.
    delay: Timer,
    timer: Stopwatch,
    visible: bool,
}

impl Default for EyeHintAnimation {
    fn default() -> Self {
        Self {
            delay: Timer::new(),
            timer: Stopwatch::new_stopped(),
            visible: false,
        }
    }
}

impl EyeHintAnimation {
    /// Pause between the first character being hidden and the slide-in.
    const START_DELAY: Duration = Duration::from_millis(200);
    /// Duration of the eye icon slide-in.
    const DURATION: Duration = Duration::from_millis(205);
    /// Delay before the hidden characters start moving, from the slide-in
    /// start.
    const CONTENT_DELAY: Duration = Duration::from_millis(65);

    /// Start the slide-in when the icon becomes visible, reset it when the
    /// icon is hidden.
    pub fn set_visible(&mut self, ctx: &mut EventCtx, visible: bool) {
        if visible == self.visible {
            return;
        }
        self.visible = visible;
        self.delay.stop();
        self.timer = Stopwatch::new_stopped();
        if visible && !animation_disabled() {
            self.delay.start(ctx, Self::START_DELAY);
        }
        ctx.request_paint();
    }

    /// Start the slide-in once the pause is over and keep requesting animation
    /// frames while it runs. Returns `true` when the input should be
    /// repainted.
    pub fn process(&mut self, ctx: &mut EventCtx, event: Event) -> bool {
        if self.delay.expire(event) {
            self.timer.start();
            ctx.request_anim_frame();
            return false;
        }
        if !matches!(event, Event::Timer(EventCtx::ANIM_FRAME_TIMER)) || !self.timer.is_running() {
            return false;
        }
        if self.timer.is_running_within(Self::DURATION) {
            ctx.request_anim_frame();
        } else {
            self.timer = Stopwatch::new_stopped();
        }
        ctx.request_paint();
        true
    }

    pub fn is_visible(&self) -> bool {
        self.visible
    }

    /// Progress of the eye icon, from 0.0 (off its place) to 1.0 (in place).
    pub fn icon_progress(&self) -> f32 {
        self.progress(Duration::ZERO)
    }

    /// Progress of the hidden characters, from 0.0 (start position) to 1.0
    /// (in place next to the icon).
    pub fn content_progress(&self) -> f32 {
        self.progress(Self::CONTENT_DELAY)
    }

    fn progress(&self, delay: Duration) -> f32 {
        if !self.visible || self.delay.is_running() {
            return 0.0;
        }
        if !self.timer.is_running() {
            return 1.0;
        }
        let elapsed = self.timer.elapsed();
        match (
            elapsed.checked_sub(delay),
            Self::DURATION.checked_sub(delay),
        ) {
            (Some(elapsed), Some(duration)) => (elapsed / duration).min(1.0),
            _ => 0.0,
        }
    }

    /// Offset of an element sliding `distance` pixels into place.
    pub fn offset(progress: f32, distance: i16) -> i16 {
        -(f32::from(distance) * (1.0 - progress)) as i16
    }
}

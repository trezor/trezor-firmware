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
    delay_timer: Timer,
    /// Measures the slide-in once it starts.
    animation_watch: Stopwatch,
    visible: bool,
}

impl Default for EyeHintAnimation {
    fn default() -> Self {
        Self {
            delay_timer: Timer::new(),
            animation_watch: Stopwatch::new_stopped(),
            visible: false,
        }
    }
}

impl EyeHintAnimation {
    /// Pause between the first character being hidden and the slide-in.
    const START_DELAY: Duration = Duration::from_millis(200);
    /// Duration of the slide-in.
    const DURATION: Duration = Duration::from_millis(205);
    /// Delay before the hidden characters start moving, from the slide-in
    /// start.
    const CONTENT_DELAY: Duration = Duration::from_millis(65);

    const INV_DURATION_MS: f32 = 1.0 / Self::DURATION.to_millis() as f32;
    /// Slide-in progress at which the hidden characters start moving.
    const CONTENT_START: f32 = Self::CONTENT_DELAY.to_millis() as f32 * Self::INV_DURATION_MS;
    const CONTENT_SCALE: f32 = 1.0 / (1.0 - Self::CONTENT_START);

    /// Start the slide-in when the icon becomes visible, reset it when the
    /// icon is hidden.
    pub fn set_visible(&mut self, ctx: &mut EventCtx, visible: bool) {
        if visible == self.visible {
            return;
        }
        self.visible = visible;
        self.delay_timer.stop();
        self.animation_watch = Stopwatch::new_stopped();
        if visible && !animation_disabled() {
            self.delay_timer.start(ctx, Self::START_DELAY);
        }
        ctx.request_paint();
    }

    /// Start the slide-in once the pause is over and keep requesting animation
    /// frames while it runs. Returns `true` when the slide-in has moved and
    /// the input needs to be repainted; repainting is left to the caller.
    pub fn process(&mut self, ctx: &mut EventCtx, event: Event) -> bool {
        if self.delay_timer.expire(event) {
            self.animation_watch.start();
            ctx.request_anim_frame();
            return false;
        }
        if !EventCtx::is_anim_frame(event) || !self.animation_watch.is_running() {
            return false;
        }
        if self.animation_watch.is_running_within(Self::DURATION) {
            ctx.request_anim_frame();
        } else {
            self.animation_watch = Stopwatch::new_stopped();
        }
        true
    }

    pub fn is_visible(&self) -> bool {
        self.visible
    }

    /// Progress of the slide-in, from 0.0 (eye icon off its place) to 1.0 (in
    /// place).
    pub fn progress(&self) -> f32 {
        if !self.visible || self.delay_timer.is_running() {
            return 0.0;
        }
        if !self.animation_watch.is_running() {
            return 1.0;
        }
        let elapsed_ms = self.animation_watch.elapsed().to_millis() as f32;
        (elapsed_ms * Self::INV_DURATION_MS).min(1.0)
    }

    /// Progress of the hidden characters for a given slide-in `progress`. They
    /// start moving after `CONTENT_DELAY` and arrive together with the icon.
    pub fn content_progress(progress: f32) -> f32 {
        ((progress - Self::CONTENT_START) * Self::CONTENT_SCALE).clamp(0.0, 1.0)
    }

    /// Offset of an element sliding `distance` pixels into place.
    pub fn offset(progress: f32, distance: i16) -> i16 {
        -(f32::from(distance) * (1.0 - progress)) as i16
    }
}

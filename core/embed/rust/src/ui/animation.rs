use crate::{
    time::{Duration, Instant},
    ui::lerp::{InvLerp, Lerp},
};

/// Running, time-based linear progression of a value.
#[derive(Clone)]
pub struct Animation<T> {
    /// Starting value.
    pub from: T,
    /// Ending value.
    pub to: T,
    /// Total duration of the animation.
    pub duration: Duration,
    /// Instant the animation was started on.
    pub started: Instant,
}

impl<T> Animation<T> {
    pub fn new(from: T, to: T, duration: Duration, started: Instant) -> Self {
        Self {
            from,
            to,
            duration,
            started,
        }
    }

    /// Time elapsed between `now` and the starting instant.
    pub fn elapsed(&self, now: Instant) -> Duration {
        now.saturating_duration_since(self.started)
    }

    /// Value of this animation at `now` instant.
    pub fn value(&self, now: Instant) -> T
    where
        T: Lerp,
    {
        let factor = self.elapsed(now) / self.duration;
        T::lerp_bounded(self.from, self.to, factor)
    }

    /// Seek the animation such that `value` would be the current value.
    pub fn seek_to_value(&mut self, value: T)
    where
        T: InvLerp,
    {
        let factor = T::inv_lerp(self.from, self.to, value);
        let offset = self.duration * factor;
        self.seek_forward(offset);
    }

    /// Seek the animation forward by moving the starting instant back in time.
    pub fn seek_forward(&mut self, offset: Duration) {
        if let Some(started) = self.started.checked_sub(offset) {
            self.started = started;
        } else {
            // Duration is too large to be added to an `Instant`.
            #[cfg(feature = "ui_debug")]
            fatal_error!("Offset is too large");
        }
    }

    pub fn finished(&self, now: Instant) -> bool {
        self.elapsed(now) >= self.duration
    }
}

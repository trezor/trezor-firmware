use rtl::unwrap;

use crate::time::instant::MAX_DIFFERENCE_IN_MILLIS;
use crate::time::{Duration, Instant, ShortDuration};

pub const MAX_TIMEOUT_MS: u32 = MAX_DIFFERENCE_IN_MILLIS;

/// Timeout value that can be infallibly converted to a deadline.
///
/// Particularly useful as an argument to functions that internally accept a
/// deadline, such as various callers of [`crate::sysevent::poll`].
#[derive(Copy, Clone, Debug, PartialEq, Eq, PartialOrd, Ord, Default)]
pub struct Timeout(Duration);

pub struct TimeoutTooLarge;

impl Timeout {
    /// Creates a new timeout from a number of milliseconds.
    pub const fn from_millis(ms: u32) -> Result<Self, TimeoutTooLarge> {
        if ms > MAX_TIMEOUT_MS {
            return Err(TimeoutTooLarge);
        }
        Ok(Self(Duration::from_millis(ms)))
    }

    /// Creates a new timeout from a number of seconds.
    pub const fn from_secs(secs: u32) -> Result<Self, TimeoutTooLarge> {
        let Some(millis) = secs.checked_mul(1000) else {
            return Err(TimeoutTooLarge);
        };
        Self::from_millis(millis)
    }

    /// Converts the timeout to a number of milliseconds.
    pub const fn to_millis(self) -> u32 {
        self.0.to_millis()
    }

    /// Converts the timeout to a deadline.
    pub fn to_deadline(self) -> Instant {
        // by construction, timeout is at most MAX_DIFFERENCE_IN_MILLIS
        // so checked_add cannot fail
        match Instant::now().checked_add(self.0) {
            Some(instant) => instant,
            None => unreachable!(),
        }
    }
}

impl TryFrom<Duration> for Timeout {
    type Error = TimeoutTooLarge;

    fn try_from(duration: Duration) -> Result<Self, Self::Error> {
        Self::from_millis(duration.to_millis())
    }
}

impl From<Timeout> for Duration {
    fn from(timeout: Timeout) -> Self {
        timeout.0
    }
}

impl From<ShortDuration> for Timeout {
    fn from(duration: ShortDuration) -> Self {
        // can't fail because ShortDuration stores a u16
        // whose max is less than MAX_TIMEOUT_MS
        unwrap!(Self::from_millis(duration.to_millis()))
    }
}

use core::{
    cmp::Ordering,
    ops::{Div, Mul},
};

use crate::trezorhal::time;

const MILLIS_PER_SEC: u32 = 1000;

#[derive(Copy, Clone, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub struct Duration {
    millis: u32,
}

impl Duration {
    pub const ZERO: Self = Self::from_millis(0);

    pub const fn from_millis(millis: u32) -> Self {
        Self { millis }
    }

    pub const fn from_secs(secs: u32) -> Self {
        Self {
            millis: secs * MILLIS_PER_SEC,
        }
    }

    pub fn to_millis(self) -> u32 {
        self.millis
    }

    pub fn checked_add(self, rhs: Self) -> Option<Self> {
        self.millis.checked_add(rhs.millis).map(Self::from_millis)
    }

    pub fn checked_sub(self, rhs: Self) -> Option<Self> {
        self.millis.checked_sub(rhs.millis).map(Self::from_millis)
    }
}

impl Mul<f32> for Duration {
    // Multiplication by float is saturating -- in particular, casting from a float
    // to an int is saturating, value larger than INT_MAX casts to INT_MAX. So
    // this operation does not need to be checked.
    type Output = Self;

    fn mul(self, rhs: f32) -> Self::Output {
        Self::from_millis((self.millis as f32 * rhs) as u32)
    }
}

impl Div<u32> for Duration {
    // Division by integer cannot overflow so it does not need to be checked.
    type Output = Self;

    fn div(self, rhs: u32) -> Self::Output {
        Self::from_millis(self.millis / rhs)
    }
}

impl Div<Duration> for Duration {
    // Division by float results in float so it does not need to be checked.
    type Output = f32;

    fn div(self, rhs: Self) -> Self::Output {
        self.to_millis() as f32 / rhs.to_millis() as f32
    }
}

/* Instants can wrap around and we want them to be comparable even after
 * wrapping around. This works by setting a maximum allowable difference
 * between two Instants to half the range. In checked_add and checked_sub, we
 * make sure that the step from one Instant to another is at most
 * MAX_DIFFERENCE_IN_MILLIS. In the Ord implementation, if the difference is
 * more than MAX_DIFFERENCE_IN_MILLIS, we can assume that the smaller Instant
 * is actually wrapped around and so is in the future. */
const MAX_DIFFERENCE_IN_MILLIS: u32 = u32::MAX / 2;

#[derive(Copy, Clone, Debug, Eq, PartialEq)]
pub struct Instant {
    millis: u32,
}

impl Instant {
    pub fn now() -> Self {
        Self {
            millis: time::ticks_ms(),
        }
    }

    pub fn saturating_duration_since(self, earlier: Self) -> Duration {
        self.checked_duration_since(earlier)
            .unwrap_or(Duration::ZERO)
    }

    pub fn checked_duration_since(self, earlier: Self) -> Option<Duration> {
        if self >= earlier {
            Some(Duration::from_millis(
                self.millis.wrapping_sub(earlier.millis),
            ))
        } else {
            None
        }
    }

    pub fn checked_add(self, duration: Duration) -> Option<Self> {
        let add_millis = duration.to_millis();
        if add_millis <= MAX_DIFFERENCE_IN_MILLIS {
            Some(Self {
                millis: self.millis.wrapping_add(add_millis),
            })
        } else {
            None
        }
    }

    pub fn checked_sub(self, duration: Duration) -> Option<Self> {
        let sub_millis = duration.to_millis();
        if sub_millis <= MAX_DIFFERENCE_IN_MILLIS {
            Some(Self {
                millis: self.millis.wrapping_sub(sub_millis),
            })
        } else {
            None
        }
    }
}

impl PartialOrd for Instant {
    fn partial_cmp(&self, rhs: &Self) -> Option<Ordering> {
        Some(self.cmp(rhs))
    }
}

impl Ord for Instant {
    fn cmp(&self, rhs: &Self) -> Ordering {
        if self.millis == rhs.millis {
            Ordering::Equal
        } else {
            // If the difference is greater than MAX_DIFFERENCE_IN_MILLIS, we assume
            // that the larger Instant is in the past.
            // See explanation on MAX_DIFFERENCE_IN_MILLIS
            self.millis
                .wrapping_sub(rhs.millis)
                .cmp(&MAX_DIFFERENCE_IN_MILLIS)
                .reverse()
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn instant_wraps_and_compares_correctly() {
        let milli = Duration { millis: 1 };
        let earlier = Instant { millis: u32::MAX };
        let later = earlier.checked_add(milli).unwrap();
        assert_eq!(later, Instant { millis: 0 });
        assert!(earlier < later);
    }
}

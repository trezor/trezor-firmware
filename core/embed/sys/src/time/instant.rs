use core::cmp::Ordering;

use super::duration::Duration;

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
            millis: super::ticks_ms(),
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

    pub fn to_millis(self) -> u32 {
        self.millis
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
                .cmp(&(MAX_DIFFERENCE_IN_MILLIS + 1))
                .reverse()
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn instant_now() {
        let instant = Instant::now();
        assert!(instant.millis <= crate::time::ticks_ms());
    }

    #[test]
    fn instant_wraps_and_compares_correctly() {
        let milli = Duration::from_millis(1);
        let earlier = Instant { millis: u32::MAX };
        let later = earlier.checked_add(milli).unwrap();
        assert_eq!(later, Instant { millis: 0 });
        assert!(earlier < later);
    }

    #[test]
    fn instant_ord_eq_consistent_at_max_difference() {
        let earlier = Instant { millis: 0 };
        let later = earlier
            .checked_add(Duration::from_millis(MAX_DIFFERENCE_IN_MILLIS))
            .unwrap();
        assert_ne!(earlier, later);
        // Difference of exactly MAX_DIFFERENCE_IN_MILLIS must not yield Equal
        // (that would break the Ord/Eq contract with derived PartialEq).
        assert_eq!(later.cmp(&earlier), Ordering::Greater);
        assert_eq!(earlier.cmp(&later), Ordering::Less);
        assert!(earlier < later);
    }
}

use core::ops::{Div, Mul};

const MILLIS_PER_SEC: u32 = 1000;
const MILLIS_PER_MINUTE: u32 = MILLIS_PER_SEC * 60;
const MILLIS_PER_HOUR: u32 = MILLIS_PER_MINUTE * 60;
const MILLIS_PER_DAY: u32 = MILLIS_PER_HOUR * 24;

#[derive(Copy, Clone, Debug, PartialEq, Eq)]
pub struct ShortDuration {
    millis: u16,
}

impl ShortDuration {
    pub const ZERO: Self = Self::from_millis(0);

    pub const fn from_millis(millis: u16) -> Self {
        Self { millis }
    }
}

#[derive(Copy, Clone, Debug, PartialEq, Eq, PartialOrd, Ord, Default)]
pub struct Duration {
    millis: u32,
}

impl Duration {
    pub const ZERO: Self = Self::from_millis(0);

    pub const fn from_millis(millis: u32) -> Self {
        Self { millis }
    }

    pub const fn from_secs(secs: u32) -> Self {
        // Check for potential overflow
        debug_assert!(secs < u32::MAX / MILLIS_PER_SEC);
        Self::from_millis(secs * MILLIS_PER_SEC)
    }

    pub const fn from_mins(mins: u32) -> Self {
        // Check for potential overflow
        debug_assert!(mins < u32::MAX / MILLIS_PER_MINUTE);
        Self::from_millis(mins * MILLIS_PER_MINUTE)
    }

    pub const fn from_hours(hours: u32) -> Self {
        // Check for potential overflow
        debug_assert!(hours < u32::MAX / MILLIS_PER_HOUR);
        Self::from_millis(hours * MILLIS_PER_HOUR)
    }
    pub const fn from_days(days: u32) -> Self {
        // Check for potential overflow
        debug_assert!(days < u32::MAX / MILLIS_PER_DAY);
        Self::from_millis(days * MILLIS_PER_DAY)
    }

    pub fn to_millis(self) -> u32 {
        self.millis
    }

    pub fn to_secs(self) -> u32 {
        self.millis / MILLIS_PER_SEC
    }
    pub fn to_mins(self) -> u32 {
        self.millis / MILLIS_PER_MINUTE
    }
    pub fn to_hours(self) -> u32 {
        self.millis / MILLIS_PER_HOUR
    }
    pub fn to_days(self) -> u32 {
        self.millis / MILLIS_PER_DAY
    }

    pub fn checked_add(self, rhs: Self) -> Option<Self> {
        self.millis.checked_add(rhs.millis).map(Self::from_millis)
    }

    pub fn checked_sub(self, rhs: Self) -> Option<Self> {
        self.millis.checked_sub(rhs.millis).map(Self::from_millis)
    }

    pub fn saturating_add(self, rhs: Self) -> Self {
        Self::from_millis(self.millis.saturating_add(rhs.millis))
    }

    /// Returns a new Duration containing only the largest complete time unit
    /// (days, hours, minutes, or seconds)
    ///
    /// Examples:
    /// - 1 day, 3 hours → 1 day
    /// - 3 hours, 45 minutes → 3 hours
    /// - 59 seconds → 59 seconds
    pub fn crop_to_largest_unit(self) -> Self {
        if self.millis >= MILLIS_PER_DAY {
            Duration::from_days(self.to_days())
        } else if self.millis >= MILLIS_PER_HOUR {
            Duration::from_hours(self.to_hours())
        } else if self.millis >= MILLIS_PER_MINUTE {
            Duration::from_mins(self.to_mins())
        } else {
            Duration::from_secs(self.to_secs())
        }
    }

    /// Increment by one unit based on the current magnitude
    ///
    /// Examples:
    /// - 59s → 1m (moves to the next unit when crossing a boundary)
    /// - 1m → 2m
    /// - 23h → 1d
    ///
    /// Returns None if addition would overflow
    pub fn increment_unit(self) -> Option<Self> {
        let base = self.crop_to_largest_unit();

        let step = if base.millis < MILLIS_PER_MINUTE {
            Duration::from_secs(1)
        } else if base.millis < MILLIS_PER_HOUR {
            Duration::from_mins(1)
        } else if base.millis < MILLIS_PER_DAY {
            Duration::from_hours(1)
        } else {
            Duration::from_days(1)
        };

        base.checked_add(step)
    }

    /// Decrement by one unit based on the current magnitude
    ///
    /// Examples:
    /// - 1m → 59s (moves to the previous unit at boundaries)
    /// - 2m → 1m
    /// - 1h → 59m
    /// - 1d → 23h
    ///
    /// Returns None if subtraction would result in negative duration
    pub fn decrement_unit(self) -> Option<Self> {
        let base = self.crop_to_largest_unit();

        let step = if base.millis <= MILLIS_PER_MINUTE {
            Duration::from_secs(1)
        } else if base.millis <= MILLIS_PER_HOUR {
            Duration::from_mins(1)
        } else if base.millis <= MILLIS_PER_DAY {
            Duration::from_hours(1)
        } else {
            Duration::from_days(1)
        };

        base.checked_sub(step)
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

impl From<ShortDuration> for Duration {
    fn from(value: ShortDuration) -> Self {
        Self::from_millis(value.millis.into())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn duration_from_millis() {
        assert_eq!(Duration::from_millis(1000), Duration::from_secs(1));
    }

    #[test]
    fn test_crop_to_largest_unit() {
        assert_eq!(
            Duration::from_secs(59).crop_to_largest_unit(),
            Duration::from_secs(59)
        );
        assert_eq!(
            Duration::from_secs(60).crop_to_largest_unit(),
            Duration::from_mins(1)
        );
        assert_eq!(
            Duration::from_secs(61).crop_to_largest_unit(),
            Duration::from_mins(1)
        );
        assert_eq!(
            Duration::from_secs(3600).crop_to_largest_unit(),
            Duration::from_hours(1)
        );
        assert_eq!(
            Duration::from_secs(86399).crop_to_largest_unit(),
            Duration::from_hours(23)
        );
    }

    #[test]
    fn test_increment_decrement_unit() {
        // Increment
        assert_eq!(
            Duration::from_secs(59).increment_unit().unwrap(),
            Duration::from_mins(1)
        );
        assert_eq!(
            Duration::from_mins(1).increment_unit().unwrap(),
            Duration::from_mins(2)
        );
        assert_eq!(
            Duration::from_secs(61).increment_unit().unwrap(),
            Duration::from_mins(2)
        );
        assert_eq!(
            Duration::from_days(3).increment_unit().unwrap(),
            Duration::from_days(4)
        );

        // Decrement
        assert_eq!(
            Duration::from_mins(1).decrement_unit().unwrap(),
            Duration::from_secs(59)
        );
        assert_eq!(
            Duration::from_secs(61).decrement_unit().unwrap(),
            Duration::from_secs(59)
        );
        assert_eq!(
            Duration::from_mins(3).decrement_unit().unwrap(),
            Duration::from_mins(2)
        );
        assert_eq!(
            Duration::from_hours(1).decrement_unit().unwrap(),
            Duration::from_mins(59)
        );
    }
}

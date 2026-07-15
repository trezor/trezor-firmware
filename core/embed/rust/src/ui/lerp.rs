/// Describes a type that can linearly interpolate (and extrapolate) based on
/// two values and a `f32` factor.
pub trait Lerp: Copy {
    /// Interpolate/extrapolate between `a` and `b` and `t` as the factor.
    fn lerp(a: Self, b: Self, t: f32) -> Self;

    /// Interpolate between `a` and `b` by bounding the factor `t` in the range
    /// `0..=1.0`.
    fn lerp_bounded(a: Self, b: Self, t: f32) -> Self
    where
        Self: Sized,
    {
        match t {
            t if t < 0.0 => a,
            t if t > 1.0 => b,
            t => Self::lerp(a, b, t),
        }
    }
}

/// Type that can compute an inverse of linear interpolation.
pub trait InvLerp: Copy {
    /// Find a factor between `0.0` and `1.0` that defines the position of
    /// `value` in the `min` and `max` closed interval.
    fn inv_lerp(min: Self, max: Self, value: Self) -> f32;
}

macro_rules! impl_lerp_for_signed {
    ($int: ident) => {
        impl Lerp for $int {
            fn lerp(a: Self, b: Self, t: f32) -> Self {
                (f32::from(a) + t * f32::from(b - a)) as Self
            }
        }

        impl InvLerp for $int {
            fn inv_lerp(min: Self, max: Self, value: Self) -> f32 {
                f32::from(value - min) / f32::from(max - min)
            }
        }
    };
}

macro_rules! impl_lerp_for_unsigned {
    ($uint: ident) => {
        impl Lerp for $uint {
            fn lerp(a: Self, b: Self, t: f32) -> Self {
                if a <= b {
                    (f32::from(a) + t * f32::from(b - a)) as Self
                } else {
                    (f32::from(a) - t * f32::from(a - b)) as Self
                }
            }
        }

        impl InvLerp for $uint {
            fn inv_lerp(min: Self, max: Self, value: Self) -> f32 {
                if min <= max {
                    f32::from(value - min) / f32::from(max - min)
                } else {
                    f32::from(value - max) / f32::from(min - max)
                }
            }
        }
    };
}

impl_lerp_for_signed!(i16);
impl_lerp_for_unsigned!(u8);
impl_lerp_for_unsigned!(u16);

impl_lerp_for_signed!(f32);

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn lerp_for_int_and_uint() {
        assert_eq!(i16::lerp(0, 8, 0.5), 4);
        assert_eq!(i16::lerp(0, 8, -1.0), -8);
        assert_eq!(i16::lerp(8, 0, 0.5), 4);
        assert_eq!(u16::lerp(0, 8, 0.5), 4);
        assert_eq!(u16::lerp(8, 0, -1.0), 16);
    }

    #[test]
    fn inv_lerp_for_int_and_uint() {
        assert!((i16::inv_lerp(0, 8, 4) - 0.5).abs() < f32::EPSILON);
        assert!((i16::inv_lerp(0, 8, -8) - -1.0).abs() < f32::EPSILON);
        assert!((i16::inv_lerp(8, 0, 4) - 0.5).abs() < f32::EPSILON);
        assert!((u16::inv_lerp(0, 8, 4) - 0.5).abs() < f32::EPSILON);
    }
}

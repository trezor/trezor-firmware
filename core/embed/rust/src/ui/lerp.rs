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

macro_rules! impl_lerp_for_int {
    ($int: ident) => {
        impl Lerp for $int {
            fn lerp(a: Self, b: Self, t: f32) -> Self {
                (a as f32 + t * (b - a) as f32) as Self
            }
        }

        impl InvLerp for $int {
            fn inv_lerp(min: Self, max: Self, value: Self) -> f32 {
                (value - min) as f32 / (max - min) as f32
            }
        }
    };
}

macro_rules! impl_lerp_for_uint {
    ($uint: ident) => {
        impl Lerp for $uint {
            fn lerp(a: Self, b: Self, t: f32) -> Self {
                if a <= b {
                    (a as f32 + t * (b - a) as f32) as Self
                } else {
                    (a as f32 - t * (a - b) as f32) as Self
                }
            }
        }

        impl InvLerp for $uint {
            fn inv_lerp(min: Self, max: Self, value: Self) -> f32 {
                if min <= max {
                    (value - min) as f32 / (max - min) as f32
                } else {
                    (value - max) as f32 / (min - max) as f32
                }
            }
        }
    };
}

impl_lerp_for_int!(i16);
impl_lerp_for_int!(i32);
impl_lerp_for_uint!(u8);
impl_lerp_for_uint!(u16);
impl_lerp_for_uint!(u32);

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn lerp_for_int_and_uint() {
        assert_eq!(i32::lerp(0, 8, 0.5), 4);
        assert_eq!(i32::lerp(0, 8, -1.0), -8);
        assert_eq!(i32::lerp(8, 0, 0.5), 4);
        assert_eq!(u32::lerp(0, 8, 0.5), 4);
        assert_eq!(u32::lerp(8, 0, -1.0), 16);
    }

    #[test]
    fn inv_lerp_for_int_and_uint() {
        assert!((i32::inv_lerp(0, 8, 4) - 0.5).abs() < f32::EPSILON);
        assert!((i32::inv_lerp(0, 8, -8) - -1.0).abs() < f32::EPSILON);
        assert!((i32::inv_lerp(8, 0, 4) - 0.5).abs() < f32::EPSILON);
        assert!((u32::inv_lerp(0, 8, 4) - 0.5).abs() < f32::EPSILON);
    }
}

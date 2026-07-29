//! Shared helpers for the lockscreen animation prototypes.
//!
//! Everything here is deliberately libm-free: the device build is `no_std` and
//! links no math library (compare the hand-written `shape::utils::sin_f32`,
//! which is a polynomial valid only over 0..45 degrees). Using `f32::sin`,
//! `fract`, `abs` or `rem_euclid` would compile for the macOS emulator and fail
//! for the device.

use crate::ui::{geometry::Rect, shape::Canvas};

/// The part of `bounds` visible in the slice the shape was handed, in
/// **absolute** screen coordinates.
///
/// `ProgressiveRenderer` translates the canvas viewport into slice-local space
/// before calling `draw()`, so a shape must clip against that viewport and then
/// translate back out. Deriving anything visual from slice-local coordinates
/// instead makes the pattern restart every 16 px, which reads as banding.
/// Same idiom as `shape::JpegImage::draw`.
pub fn visible_abs(canvas: &dyn Canvas, bounds: Rect) -> Rect {
    let clip = canvas.viewport().relative_clip(bounds).clip;
    clip.translate(-canvas.viewport().origin)
}

/// Fractional part of `x`, for any sign.
pub fn fract(x: f32) -> f32 {
    let f = x - (x as i32) as f32;
    if f < 0.0 {
        f + 1.0
    } else {
        f
    }
}

/// Absolute value.
pub fn absf(x: f32) -> f32 {
    if x < 0.0 {
        -x
    } else {
        x
    }
}

/// Larger of two values.
pub fn maxf(a: f32, b: f32) -> f32 {
    if a > b {
        a
    } else {
        b
    }
}

/// Clamp to 0..1.
pub fn saturate(x: f32) -> f32 {
    if x < 0.0 {
        0.0
    } else if x > 1.0 {
        1.0
    } else {
        x
    }
}

/// Sine of `t` **turns** (1.0 == a full period), approximated by the parabola
/// `4u(1-u)` over each half period. Peak error against a true sine is a few
/// percent — inaudible for animation, and it costs two multiplies.
pub fn sin_turns(t: f32) -> f32 {
    let x = fract(t);
    if x < 0.5 {
        let u = x * 2.0;
        4.0 * u * (1.0 - u)
    } else {
        let u = (x - 0.5) * 2.0;
        -4.0 * u * (1.0 - u)
    }
}

/// Cosine of `t` turns.
pub fn cos_turns(t: f32) -> f32 {
    sin_turns(t + 0.25)
}

/// Integer bit-mix (variant of the "lowbias32" finalizer).
pub fn hash_u32(mut x: u32) -> u32 {
    x ^= x >> 16;
    x = x.wrapping_mul(0x7feb_352d);
    x ^= x >> 15;
    x = x.wrapping_mul(0x846c_a68b);
    x ^= x >> 16;
    x
}

/// Hash to a float in 0..1.
pub fn hash_f(seed: u32) -> f32 {
    (hash_u32(seed) >> 8) as f32 / 16_777_216.0
}

fn smoothstep(t: f32) -> f32 {
    t * t * (3.0 - 2.0 * t)
}

/// 1-D value noise in 0..1: a smooth pseudo-random curve in `x`.
///
/// `x` must be non-negative — the integer cast truncates toward zero rather
/// than flooring, so negative inputs would fold the curve back on itself. All
/// callers here derive `x` from elapsed time plus a positive offset.
pub fn noise1(seed: u32, x: f32) -> f32 {
    let i = x as i32;
    let f = x - i as f32;
    let k = |n: i32| hash_f(seed ^ (n as u32).wrapping_mul(2_654_435_761));
    let a = k(i);
    let b = k(i + 1);
    a + (b - a) * smoothstep(f)
}

/// Fast sine approximation.
///
/// Returns sin(angle).
///
/// Angle must be in range <0..45>.
pub fn sin_f32(angle: f32) -> f32 {
    assert!((0.0..=45.0).contains(&angle));

    // Applying the approximation x - x^3 / 6
    let x = (angle / 180.0) * core::f32::consts::PI;
    x - x * x * x / 6.0
}

/// Sine and cosine of an arbitrary angle given in degrees.
///
/// Returns (sin(angle), cos(angle)), accurate to ~4e-5.
pub fn sin_cos_f32(angle: f32) -> (f32, f32) {
    let a = (360.0 + angle % 360.0) % 360.0;
    let quadrant = (a / 90.0) as i32;
    let rem = a - 90.0 * quadrant as f32;

    // Taylor series on <0..45> degrees, mirrored for <45..90>
    let sin_cos = |deg: f32| -> (f32, f32) {
        let x = (deg / 180.0) * core::f32::consts::PI;
        let x2 = x * x;
        let s = x * (1.0 - x2 / 6.0 * (1.0 - x2 / 20.0));
        let c = 1.0 - x2 / 2.0 * (1.0 - x2 / 12.0 * (1.0 - x2 / 30.0));
        (s, c)
    };

    let (s, c) = if rem <= 45.0 {
        sin_cos(rem)
    } else {
        let (s, c) = sin_cos(90.0 - rem);
        (c, s)
    };

    match quadrant {
        0 => (s, c),
        1 => (c, -s),
        2 => (-s, -c),
        _ => (-c, s),
    }
}

/// Square root of a non-negative number.
pub fn sqrt_f32(x: f32) -> f32 {
    // Compiles to a single FPU instruction on the hardware
    core::f32::math::sqrt(x.max(0.0))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn sin_cos() {
        for deg in -720..=720 {
            let rad = (deg as f32).to_radians();
            let (s, c) = sin_cos_f32(deg as f32);
            assert!((s - rad.sin()).abs() < 1e-4, "sin({})", deg);
            assert!((c - rad.cos()).abs() < 1e-4, "cos({})", deg);
        }
    }

    #[test]
    fn sqrt() {
        for i in 0..100_000 {
            let x = i as f32 * 0.37;
            assert!((sqrt_f32(x) - x.sqrt()).abs() <= x.sqrt() * 1e-6 + 1e-6);
        }
    }
}

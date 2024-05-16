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

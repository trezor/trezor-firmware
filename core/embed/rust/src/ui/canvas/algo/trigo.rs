/// Integer representing an angle of 45 degress (PI/4).
//
// Changing this constant requires revisiting isin() algorithm
// (for higher values consider changing T type to i64 or f32)
pub const PI4: i16 = 45;

/// Fast sine approximation.
///
/// Returns mult * sin(angle).
///
/// Angle must be in range <0..PI4>.
/// This function provides an error within +-1 for multiplier up to 500
pub fn sin_i16(angle: i16, mult: i16) -> i16 {
    assert!(angle >= 0 && angle <= PI4);
    assert!(mult <= 2500);

    type T = i32;

    // Based on polynomial x - x^3 / 6
    let x = angle as T;

    // Constants for the approximation
    const K: f32 = (PI4 as f32) * 4.0 / core::f32::consts::PI;
    const M: T = (6.0 * K * K + 0.5) as T;
    const N: T = (6.0 * K * K * K + 0.5) as T;

    // Applying the approximation
    (((M * x - x * x * x) * mult as T + N / 2) / N) as i16
}

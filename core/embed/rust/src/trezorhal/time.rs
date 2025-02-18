use crate::time::Duration;

use super::ffi;

/// Returns the current time in milliseconds since the device was reset.
/// Time is represented as a 32-bit number that wraps around every 49.7 days.
pub fn ticks_ms() -> u32 {
    unsafe { ffi::systick_ms() as _ }
}

/// Returns the current time in microseconds since the device was reset.
/// Time is represented as a 64-bit number and never wraps around.
pub fn ticks_us() -> u64 {
    unsafe { ffi::systick_us() as _ }
}

/// Sleeps for the specified duration.
pub fn sleep(delay: Duration) {
    unsafe {
        ffi::systick_delay_ms(delay.to_millis() as _);
    }
}

/// Measures the time it takes to execute a closure in microseconds.
pub fn measure_us(f: impl FnOnce()) -> u64 {
    let start = ticks_us();
    f();
    ticks_us() - start
}

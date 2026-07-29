use crate::ffi;

mod duration;
mod instant;

pub use duration::{Duration, ShortDuration};
pub use instant::Instant;

pub fn ticks_ms() -> u32 {
    // SAFETY: safe
    unsafe { ffi::systick_ms() as _ }
}

pub fn ticks_us() -> u64 {
    // SAFETY: safe
    unsafe { ffi::systick_us() as _ }
}

pub fn sleep_ms(ms: u32) {
    // SAFETY: safe
    unsafe { ffi::systick_delay_ms(ms) }
}

pub fn sleep_us(us: u64) {
    // SAFETY: safe
    unsafe { ffi::systick_delay_us(us) }
}

pub fn sleep(duration: Duration) {
    sleep_ms(duration.to_millis());
}

/// Measures the time it takes to execute a closure in microseconds.
pub fn measure_us(f: impl FnOnce()) -> u64 {
    let start = ticks_us();
    f();
    ticks_us() - start
}

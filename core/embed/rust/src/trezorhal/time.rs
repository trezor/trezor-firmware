use crate::time::Duration;

use super::ffi;

pub fn ticks_ms() -> u32 {
    unsafe { ffi::hal_ticks_ms() as _ }
}

pub fn sleep(delay: Duration) {
    unsafe {
        ffi::hal_delay(delay.to_millis() as _);
    }
}

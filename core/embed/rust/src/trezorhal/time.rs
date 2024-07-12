use crate::time::Duration;

use super::ffi;

pub fn ticks_ms() -> u32 {
    unsafe { ffi::systick_ms() as _ }
}

pub fn sleep(delay: Duration) {
    unsafe {
        ffi::systick_delay_ms(delay.to_millis() as _);
    }
}

use super::ffi;
use crate::time::Duration;

pub fn ticks_ms() -> u32 {
    unsafe { ffi::mp_hal_ticks_ms() as _ }
}

pub fn sleep(delay: Duration) {
    unsafe { ffi::mp_hal_delay_ms(delay.to_millis() as _) }
}

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

pub fn get_ticks() {
    unsafe {
        ffi::get_ticks();
    }
}
pub fn init_ticks() {
    unsafe {
        ffi::init_ticks();
    }
}
pub fn clear_acc() {
    unsafe {
        ffi::clear_acc();
    }
}

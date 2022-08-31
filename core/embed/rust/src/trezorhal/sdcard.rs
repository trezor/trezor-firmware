use super::ffi;

pub fn is_present() -> bool {
    unsafe { ffi::sdcard_is_present() != 0 }
}

pub fn power_on() -> bool {
    unsafe { ffi::sdcard_power_on() == ffi::sectrue }
}

pub fn power_off() {
    unsafe {
        ffi::sdcard_power_off();
    }
}

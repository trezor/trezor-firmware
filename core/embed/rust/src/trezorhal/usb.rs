use super::ffi;

pub fn usb_configured() -> bool {
    unsafe { ffi::usb_configured() == ffi::sectrue }
}

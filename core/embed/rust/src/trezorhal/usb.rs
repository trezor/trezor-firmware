use super::ffi;

pub fn usb_configured() -> bool {
    unsafe {
        let mut state: ffi::usb_state_t = core::mem::zeroed();
        ffi::usb_get_state(&mut state as *mut ffi::usb_state_t);
        state.configured
    }
}

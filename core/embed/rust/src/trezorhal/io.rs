use super::ffi;

#[cfg(feature = "touch")]
pub fn io_touch_get_event() -> u32 {
    unsafe { ffi::touch_get_event() }
}

#[cfg(feature = "button")]
pub fn io_button_read() -> u32 {
    unsafe { ffi::button_read() }
}

use super::ffi;

#[cfg(feature = "touch")]
pub fn io_touch_read() -> u32 {
    unsafe { ffi::touch_read() }
}

#[cfg(feature = "button")]
pub fn io_button_read() -> u32 {
    unsafe { ffi::button_read() }
}

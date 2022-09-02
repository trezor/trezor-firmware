use super::ffi;


pub fn io_touch_read() -> u32 {
    unsafe { ffi::touch_read() }
}

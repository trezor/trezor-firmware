use super::ffi;

pub fn io_touch_read() -> u32 {
    unsafe { ffi::touch_read() }
}
pub fn io_touch_unpack_x(event: u32) -> u16 {
    unsafe { ffi::touch_unpack_x(event) }
}
pub fn io_touch_unpack_y(event: u32) -> u16 {
    unsafe { ffi::touch_unpack_y(event) }
}
pub fn io_button_read() -> u32 {
    unsafe { ffi::button_read() }
}

use super::ffi;

pub fn touch_get_event() -> u32 {
    unsafe { ffi::touch_get_event() }
}

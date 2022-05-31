use super::ffi;

pub fn set_color(color: u32) {
    unsafe {
        ffi::rgb_led_set_color(color);
    }
}

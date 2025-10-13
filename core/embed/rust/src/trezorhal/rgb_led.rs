#![allow(dead_code)]

#[cfg(feature = "ui")]
use crate::ui::display::Color;

use super::ffi;

pub fn set_color(color: u32) {
    unsafe {
        ffi::rgb_led_set_color(color);
    }
}

/// Set LED color if provided, otherwise turn the LED off.
#[cfg(feature = "ui")]
pub fn set(color: Color) {
    set_color(color.to_u32());
}

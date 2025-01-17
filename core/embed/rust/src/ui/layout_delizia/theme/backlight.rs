#[cfg(not(feature = "bootloader"))]
use crate::storage;

// Typical backlight values.
const BACKLIGHT_NORMAL: u8 = 150;
const BACKLIGHT_LOW: u8 = 45;
const BACKLIGHT_DIM: u8 = 5;
const BACKLIGHT_NONE: u8 = 0;
const BACKLIGHT_MIN: u8 = 10;
const BACKLIGHT_MAX: u8 = 255;

#[cfg(feature = "bootloader")]
pub fn get_backlight_normal() -> u8 {
    BACKLIGHT_NORMAL
}

#[cfg(not(feature = "bootloader"))]
pub fn get_backlight_normal() -> u8 {
    storage::get_brightness()
        .unwrap_or(BACKLIGHT_NORMAL)
        .clamp(BACKLIGHT_MIN, BACKLIGHT_MAX)
}

#[cfg(feature = "bootloader")]
pub fn get_backlight_low() -> u8 {
    BACKLIGHT_LOW
}

#[cfg(not(feature = "bootloader"))]
pub fn get_backlight_low() -> u8 {
    storage::get_brightness()
        .unwrap_or(BACKLIGHT_LOW)
        .clamp(BACKLIGHT_MIN, BACKLIGHT_LOW)
}

pub fn get_backlight_dim() -> u8 {
    BACKLIGHT_DIM
}

pub fn get_backlight_none() -> u8 {
    BACKLIGHT_NONE
}

pub fn get_backlight_max() -> u8 {
    BACKLIGHT_MAX
}

pub fn get_backlight_min() -> u8 {
    BACKLIGHT_MIN
}

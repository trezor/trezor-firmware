#[cfg(not(feature = "bootloader"))]
use crate::storage;

// Typical backlight values.
const BACKLIGHT_NORMAL: u8 = 150;
const BACKLIGHT_LOW: u8 = 45;
const BACKLIGHT_DIM: u8 = 5;
const BACKLIGHT_NONE: u8 = 2;
const BACKLIGHT_MIN: u8 = 10;
const BACKLIGHT_MAX: u8 = 255;

#[cfg(feature = "bootloader")]
pub fn get_backlight_normal() -> u16 {
    BACKLIGHT_NORMAL.into()
}

#[cfg(not(feature = "bootloader"))]
pub fn get_backlight_normal() -> u16 {
    storage::get_brightness()
        .unwrap_or(BACKLIGHT_NORMAL)
        .clamp(BACKLIGHT_MIN, BACKLIGHT_MAX)
        .into()
}

#[cfg(feature = "bootloader")]
pub fn get_backlight_low() -> u16 {
    BACKLIGHT_LOW.into()
}

#[cfg(not(feature = "bootloader"))]
pub fn get_backlight_low() -> u16 {
    storage::get_brightness()
        .unwrap_or(BACKLIGHT_LOW)
        .clamp(BACKLIGHT_MIN, BACKLIGHT_LOW)
        .into()
}

pub fn get_backlight_dim() -> u16 {
    BACKLIGHT_DIM.into()
}

pub fn get_backlight_none() -> u16 {
    BACKLIGHT_NONE.into()
}

pub fn get_backlight_max() -> u16 {
    BACKLIGHT_MAX.into()
}

pub fn get_backlight_min() -> u16 {
    BACKLIGHT_MIN.into()
}

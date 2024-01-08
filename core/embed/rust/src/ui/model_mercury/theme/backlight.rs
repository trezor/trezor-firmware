#[cfg(not(feature = "bootloader"))]
use crate::storage;

// Typical backlight values.

#[cfg(feature = "bootloader")]
pub fn get_backlight_normal() -> u16 {
    150
}

#[cfg(not(feature = "bootloader"))]
pub fn get_backlight_normal() -> u16 {
    storage::get_brightness().unwrap_or(150).into()
}

#[cfg(feature = "bootloader")]
pub fn get_backlight_low() -> u16 {
    150
}

#[cfg(not(feature = "bootloader"))]
pub fn get_backlight_low() -> u16 {
    let val = storage::get_brightness();
    return if val.is_ok() && val.unwrap() < 45 {
        val.unwrap().into()
    } else {
        45
    };
}

pub fn get_backlight_dim() -> u16 {
    5
}

pub fn get_backlight_none() -> u16 {
    2
}

pub fn get_backlight_max() -> u16 {
    255
}

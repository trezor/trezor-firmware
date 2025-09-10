#![allow(dead_code)]

use super::ffi;

pub fn set_color(color: u32) {
    unsafe {
        ffi::rgb_led_set_color(color);
    }
}

#[derive(PartialEq, Eq, Copy, Clone)]
pub enum RgbLedEffect {
    None = ffi::rgb_led_effect_type_t_RGB_LED_EFFECT_NONE as _,
    Pairing = ffi::rgb_led_effect_type_t_RGB_LED_EFFECT_PAIRING as _,
    Charging = ffi::rgb_led_effect_type_t_RGB_LED_EFFECT_CHARGING as _,
}

pub fn effect_start(effect_type: RgbLedEffect, requested_cycles: u32) {
    unsafe {
        ffi::rgb_led_effect_start(effect_type as _, requested_cycles);
    }
}

pub fn effect_stop() {
    unsafe {
        ffi::rgb_led_effect_stop();
    }
}

pub fn effect_ongoing() -> bool {
    unsafe { ffi::rgb_led_effect_ongoing() }
}

pub fn effect_get_type() -> RgbLedEffect {
    let effect_type = unsafe { ffi::rgb_led_effect_get_type() };
    match effect_type {
        ffi::rgb_led_effect_type_t_RGB_LED_EFFECT_NONE => RgbLedEffect::None,
        ffi::rgb_led_effect_type_t_RGB_LED_EFFECT_PAIRING => RgbLedEffect::Pairing,
        ffi::rgb_led_effect_type_t_RGB_LED_EFFECT_CHARGING => RgbLedEffect::Charging,
        _ => panic!("Unknown RGB LED effect type"),
    }
}

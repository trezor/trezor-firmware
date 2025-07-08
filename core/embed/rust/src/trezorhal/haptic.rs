use super::ffi;

#[derive(PartialEq, Debug, Eq, FromPrimitive, Clone, Copy)]
pub enum HapticEffect {
    ButtonPress = ffi::haptic_effect_t_HAPTIC_BUTTON_PRESS as _,
    HoldToConfirm = ffi::haptic_effect_t_HAPTIC_HOLD_TO_CONFIRM as _,
    BootloaderEntry = ffi::haptic_effect_t_HAPTIC_BOOTLOADER_ENTRY as _,
}

pub fn play(effect: HapticEffect) {
    unsafe {
        ffi::haptic_play(effect as _);
    }
}

pub fn play_custom(amplitude_pct: i8, duration_ms: u16) {
    unsafe {
        ffi::haptic_play_custom(amplitude_pct, duration_ms);
    }
}

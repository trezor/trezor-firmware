use super::ffi;

#[derive(PartialEq, Debug, Eq, FromPrimitive, Clone, Copy)]
pub enum HapticEffect {
    ButtonPress = ffi::haptic_effect_t_HAPTIC_BUTTON_PRESS as _,
    HoldToConfirm = ffi::haptic_effect_t_HAPTIC_HOLD_TO_CONFIRM as _,
}

pub fn play(effect: HapticEffect) {
    unsafe {
        ffi::haptic_play(effect as _);
    }
}

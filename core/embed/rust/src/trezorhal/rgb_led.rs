use super::ffi;

pub fn set_color(color: u32) {
    unsafe {
        // also stops ongoing LED effect (if previously started)
        ffi::rgb_led_set_color(color);
    }
}

#[derive(PartialEq, Eq, Clone, Copy)]
pub enum Effect {
    Pairing,
    Charging,
}

impl Effect {
    pub fn set(&self) {
        if Some(self) == Self::current().as_ref() {
            // don't stop ongoing LED effect (if previously started).
            return;
        }
        let effect_type = match self {
            Effect::Pairing => ffi::rgb_led_effect_type_t_RGB_LED_EFFECT_PAIRING,
            Effect::Charging => ffi::rgb_led_effect_type_t_RGB_LED_EFFECT_CHARGING,
        };
        unsafe { ffi::rgb_led_effect_start(effect_type, 0) }
    }

    /// return current effect (if previously started).
    fn current() -> Option<Self> {
        let effect_type = unsafe { ffi::rgb_led_effect_get_type() };
        Some(match effect_type {
            ffi::rgb_led_effect_type_t_RGB_LED_EFFECT_PAIRING => Effect::Pairing,
            ffi::rgb_led_effect_type_t_RGB_LED_EFFECT_CHARGING => Effect::Charging,
            _ => return None,
        })
    }
}

pub use crate::trezorhal::rgb_led::Effect;

use crate::trezorhal::rgb_led::set_color;

use super::display::Color;

#[derive(PartialEq, Eq, Clone, Copy)]
pub enum LedState {
    Static(Color),
    Effect(Effect),
}

impl Default for LedState {
    fn default() -> Self {
        LedState::Static(Color::black())
    }
}

impl LedState {
    pub fn set(&self) {
        match self {
            Self::Static(color) => set_color(color.to_u32()),
            Self::Effect(effect) => effect.set(),
        }
    }
}

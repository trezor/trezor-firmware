use super::ffi;

use num_traits::FromPrimitive;

#[derive(Copy, Clone, PartialEq, Eq, FromPrimitive)]
#[cfg_attr(feature = "debug", derive(ufmt::derive::uDebug))]
pub enum PhysicalButton {
    Left = ffi::button_t_BTN_LEFT as _,
    Right = ffi::button_t_BTN_RIGHT as _,
    Power = ffi::button_t_BTN_POWER as _,
}

#[derive(Copy, Clone, PartialEq, Eq, FromPrimitive)]
#[cfg_attr(feature = "debug", derive(ufmt::derive::uDebug))]
pub enum PhysicalButtonEvent {
    Down = ffi::button_event_type_t_BTN_EVENT_DOWN as _,
    Up = ffi::button_event_type_t_BTN_EVENT_UP as _,
}

pub fn button_get_event() -> Option<(PhysicalButton, PhysicalButtonEvent)> {
    unsafe {
        let mut e = ffi::button_event_t {
            event_type: ffi::button_event_type_t_BTN_EVENT_DOWN,
            button: ffi::button_t_BTN_LEFT,
        };
        if ffi::button_get_event(&mut e as _) {
            Some((
                unwrap!(PhysicalButton::from_u8(e.button as _)),
                unwrap!(PhysicalButtonEvent::from_u8(e.event_type as _)),
            ))
        } else {
            None
        }
    }
}

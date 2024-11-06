use super::ffi;

#[cfg(feature = "touch")]
pub fn io_touch_get_event() -> u32 {
    unsafe { ffi::touch_get_event() }
}

#[cfg(feature = "button")]
pub fn io_button_get_event() -> u32 {
    unsafe { ffi::button_get_event() }
}

#[cfg(feature = "button")]
#[derive(Copy, Clone, PartialEq, Eq, FromPrimitive)]
#[cfg_attr(feature = "debug", derive(ufmt::derive::uDebug))]
pub enum PhysicalButton {
    Left = ffi::button_t_BTN_LEFT as _,
    Right = ffi::button_t_BTN_RIGHT as _,
    Power = ffi::button_t_BTN_POWER as _,
}

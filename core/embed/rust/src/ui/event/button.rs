pub use crate::trezorhal::button::PhysicalButton;
use crate::trezorhal::button::PhysicalButtonEvent;

#[derive(Copy, Clone, PartialEq, Eq)]
#[cfg_attr(feature = "debug", derive(ufmt::derive::uDebug))]
pub enum ButtonEvent {
    /// Button pressed down.
    /// ▼ * | * ▼
    ButtonPressed(PhysicalButton),
    /// Button released up.
    /// ▲ * | * ▲
    ButtonReleased(PhysicalButton),

    HoldStarted,
    HoldEnded,
    HoldCanceled,
}

impl ButtonEvent {
    pub fn new(event: PhysicalButtonEvent, button: PhysicalButton) -> Self {
        match event {
            PhysicalButtonEvent::Down => Self::ButtonPressed(button),
            PhysicalButtonEvent::Up => Self::ButtonReleased(button),
        }
    }
}

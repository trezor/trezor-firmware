use crate::error::Error;
use num_traits::FromPrimitive;

pub use crate::trezorhal::io::PhysicalButton;

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
}

impl ButtonEvent {
    pub fn new(event: u32, button: u32) -> Result<Self, Error> {
        let button = PhysicalButton::from_u32(button);

        let button = button.ok_or(Error::OutOfRange)?;

        let result = match event & 0xFF {
            1 => Self::ButtonPressed(button),
            2 => Self::ButtonReleased(button),
            _ => return Err(Error::OutOfRange),
        };
        Ok(result)
    }
}

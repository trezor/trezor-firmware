use crate::error::Error;

#[derive(Copy, Clone, PartialEq, Eq)]
#[cfg_attr(feature = "debug", derive(ufmt::derive::uDebug))]
pub enum PhysicalButton {
    Left,
    Right,
}

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
        let button = match button {
            0 => PhysicalButton::Left,
            1 => PhysicalButton::Right,
            _ => return Err(Error::OutOfRange),
        };
        let result = match event {
            1 => Self::ButtonPressed(button),
            2 => Self::ButtonReleased(button),
            _ => return Err(Error::OutOfRange),
        };
        Ok(result)
    }
}

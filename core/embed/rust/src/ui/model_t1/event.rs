use crate::error;

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum T1Button {
    Left,
    Right,
}

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum ButtonEvent {
    ButtonPressed(T1Button),
    ButtonReleased(T1Button),
}

impl ButtonEvent {
    pub fn new(event: u32, button: u32) -> Result<Self, error::Error> {
        let button = match button {
            0 => T1Button::Left,
            1 => T1Button::Right,
            _ => return Err(error::Error::OutOfRange),
        };
        let result = match event {
            1 => Self::ButtonPressed(button),
            2 => Self::ButtonReleased(button),
            _ => return Err(error::Error::OutOfRange),
        };
        Ok(result)
    }
}

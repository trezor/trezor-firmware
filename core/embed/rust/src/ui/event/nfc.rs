use crate::ui::UIError;

#[derive(Copy, Clone, PartialEq, Eq)]
#[cfg_attr(feature = "debug", derive(ufmt::derive::uDebug))]
pub enum NfcEvent {
    Connected,
    Disconnected,
}

impl NfcEvent {
    pub fn new(event: u32) -> Result<Self, UIError> {
        let result = match event {
            1 => Self::Connected,
            2 => Self::Disconnected,
            _ => return Err(UIError::InvalidValue),
        };
        Ok(result)
    }
}

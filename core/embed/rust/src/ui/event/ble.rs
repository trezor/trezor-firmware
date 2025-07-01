use crate::error::Error;

#[derive(Copy, Clone, PartialEq, Eq)]
#[cfg_attr(feature = "debug", derive(ufmt::derive::uDebug))]
pub enum BLEEvent {
    Connected,
    Disconnected,
    ConnectionChanged,
    PairingRequest(u32),
    PairingCanceled,
    PairingCompleted,
}

impl BLEEvent {
    pub fn new(event: u32, data: Option<u32>) -> Result<Self, Error> {
        let result = match (event, data) {
            (1, None) => Self::Connected,
            (2, None) => Self::Disconnected,
            (3, Some(code)) => Self::PairingRequest(code),
            (4, None) => Self::PairingCanceled,
            (5, None) => Self::PairingCompleted,
            (6, None) => Self::ConnectionChanged,
            _ => return Err(Error::ValueError(c"Invalid BLE event")),
        };
        Ok(result)
    }
}

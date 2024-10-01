use crate::error::Error;

#[derive(Copy, Clone, PartialEq, Eq)]
#[cfg_attr(feature = "debug", derive(ufmt::derive::uDebug))]
pub enum BLEEvent {
    Connected,
    Disconnected,
    PairingRequest(&'static [u8]),
}

impl BLEEvent {
    pub fn new(event: u32, data: &'static [u8]) -> Result<Self, Error> {
        let result = match event {
            1 => Self::Connected,
            2 => Self::Disconnected,
            3 => Self::PairingRequest(data),
            _ => return Err(Error::OutOfRange),
        };
        Ok(result)
    }
}

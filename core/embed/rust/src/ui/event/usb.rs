use crate::error::Error;

#[derive(Copy, Clone, PartialEq, Eq)]
#[cfg_attr(feature = "debug", derive(ufmt::derive::uDebug))]
pub enum USBEvent {
    /// USB host has connected/disconnected.
    Configured,
    Deconfigured,
}

impl USBEvent {
    pub fn new(event: u32) -> Result<Self, Error> {
        let result = match event {
            1 => Self::Configured,
            2 => Self::Deconfigured,
            _ => return Err(Error::OutOfRange),
        };
        Ok(result)
    }
}

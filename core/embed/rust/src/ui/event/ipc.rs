use crate::error::Error;

#[derive(Copy, Clone, PartialEq, Eq)]
#[cfg_attr(feature = "debug", derive(ufmt::derive::uDebug))]
pub enum IpcEvent {
    Received,
}

impl IpcEvent {
    pub fn new() -> Result<Self, Error> {
        let result = Self::Received;
        Ok(result)
    }
}

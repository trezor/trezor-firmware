use crate::error::Error;

#[derive(Copy, Clone, PartialEq, Eq)]
#[cfg_attr(feature = "debug", derive(ufmt::derive::uDebug))]
pub enum IpcEvent {
    Received(u32),
}

impl IpcEvent {
    pub fn new(id: u32) -> Result<Self, Error> {
        let result = Self::Received(id);
        Ok(result)
    }
}

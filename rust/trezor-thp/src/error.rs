#[derive(Clone, Copy, Debug, PartialEq)]
#[repr(u8)]
pub enum TransportError {
    TransportBusy = 1,
    UnallocatedChannel = 2,
    DecryptionFailed = 3,
    DeviceLocked = 5,
}

impl TryFrom<u8> for TransportError {
    type Error = Error;

    fn try_from(val: u8) -> Result<Self> {
        Ok(match val {
            1 => Self::TransportBusy,
            2 => Self::UnallocatedChannel,
            3 => Self::DecryptionFailed,
            5 => Self::DeviceLocked,
            _ => return Err(Error::OutOfBounds),
        })
    }
}

#[derive(Debug)]
pub enum Error {
    /// Numeric field has forbidden value.
    OutOfBounds,
    /// Invalid data/operation from crate user.
    UnexpectedInput,
    /// Invalid data from the wire.
    MalformedData,
    /// Checksum doesn't match.
    InvalidDigest,
    /// Provided buffer is too small.
    InsufficientBuffer,
}

pub type Result<T> = core::result::Result<T, Error>;

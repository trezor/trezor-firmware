#[derive(Clone, Copy, Debug, PartialEq)]
#[repr(u8)]
pub enum TransportError {
    Unknown = 0, // actually reserved, used as default value when parsing unknown errors
    TransportBusy = 1,
    UnallocatedChannel = 2,
    DecryptionFailed = 3,
    DeviceLocked = 5,
}

// TODO use num_traits::FromPrimitive
impl From<u8> for TransportError {
    fn from(val: u8) -> Self {
        match val {
            1 => Self::TransportBusy,
            2 => Self::UnallocatedChannel,
            3 => Self::DecryptionFailed,
            5 => Self::DeviceLocked,
            _ => Self::Unknown,
        }
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

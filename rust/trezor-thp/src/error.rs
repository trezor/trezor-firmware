use trezor_noise_protocol::{Error as NoiseError, ErrorKind as NoiseErrorKind};

#[cfg_attr(any(test, debug_assertions), derive(Debug))]
#[derive(Clone, Copy, PartialEq)]
#[repr(u8)]
pub enum TransportError {
    TransportBusy = 1,
    UnallocatedChannel = 2,
    DecryptionFailed = 3,
    DeviceLocked = 5,
}

impl TryFrom<&u8> for TransportError {
    type Error = Error;

    fn try_from(val: &u8) -> Result<Self> {
        Ok(match *val {
            1 => Self::TransportBusy,
            2 => Self::UnallocatedChannel,
            3 => Self::DecryptionFailed,
            5 => Self::DeviceLocked,
            _ => return Err(Error::OutOfBounds),
        })
    }
}

#[cfg_attr(any(test, debug_assertions), derive(Debug))]
#[derive(PartialEq)]
pub enum Error {
    /// Numeric field has forbidden value.
    OutOfBounds,
    /// Invalid data/operation from crate user.
    UnexpectedInput,
    /// Channel is not ready to send another message, or there is no message ready to be passed to caller.
    NotReady,
    /// Invalid data from the wire.
    MalformedData,
    /// Checksum doesn't match.
    InvalidDigest,
    /// Provided buffer is too small.
    InsufficientBuffer,
    /// Noise protocol failed.
    HandshakeFailed,
}

impl From<NoiseError> for Error {
    fn from(val: NoiseError) -> Self {
        match val.kind() {
            NoiseErrorKind::DH | NoiseErrorKind::Decryption => Self::HandshakeFailed,
            NoiseErrorKind::NeedPSK => panic!(),
            NoiseErrorKind::TooShort => Self::MalformedData,
        }
    }
}

pub type Result<T> = core::result::Result<T, Error>;

use trezor_noise_protocol::{Error as NoiseError, ErrorKind as NoiseErrorKind};

/// Payload of `transport_error` message type (0x42).
#[cfg_attr(any(test, debug_assertions), derive(Debug))]
#[derive(Clone, Copy, PartialEq)]
#[repr(u8)]
pub enum TransportError {
    /// Issued by the recipient when the transport layer is busy reassembling a message
    /// on another channel.
    TransportBusy = 1,
    /// Issued by Trezor in response to a message that has a channel identifier which
    /// is not allocated.
    UnallocatedChannel = 2,
    /// Issued by Trezor in response to a message that has an invalid authentication tag.
    DecryptionFailed = 3,
    /// Issued by Trezor in response to handshake messages (`HandshakeInitiationRequest`,
    /// `HandshakeContinuationRequest``) received while the device is locked.
    DeviceLocked = 5,
}

impl TransportError {
    pub fn is_recoverable(&self) -> bool {
        matches!(
            self,
            TransportError::TransportBusy | TransportError::DeviceLocked
        )
    }
}

impl TryFrom<u8> for TransportError {
    type Error = Error;

    fn try_from(val: u8) -> Result<Self> {
        Ok(match val {
            1 => Self::TransportBusy,
            2 => Self::UnallocatedChannel,
            3 => Self::DecryptionFailed,
            5 => Self::DeviceLocked,
            _ => return Err(Error::out_of_bounds()),
        })
    }
}

impl TryFrom<&[u8]> for TransportError {
    type Error = Error;

    fn try_from(val: &[u8]) -> Result<Self> {
        val.first()
            .ok_or_else(Error::malformed_data)
            .and_then(|b| TransportError::try_from(*b))
    }
}

#[cfg_attr(any(test, debug_assertions), derive(Debug))]
#[derive(PartialEq)]
pub enum Error {
    /// Numeric field has forbidden value.
    OutOfBounds,
    /// Invalid data/operation from crate user.
    UnexpectedInput,
    /// Channel is not ready to send another message, or there is no message ready to be passed
    /// to the caller.
    NotReady,
    /// Invalid data from the wire.
    MalformedData,
    /// Checksum doesn't match.
    InvalidDigest,
    /// Provided buffer is too small.
    InsufficientBuffer,
    /// Secure channel cryptography failed.
    CryptoError,
}

impl From<NoiseError> for Error {
    fn from(val: NoiseError) -> Self {
        match val.kind() {
            NoiseErrorKind::DH | NoiseErrorKind::Decryption => Self::crypto_error(),
            NoiseErrorKind::NeedPSK => panic!(),
            NoiseErrorKind::TooShort => Self::MalformedData,
        }
    }
}

pub type Result<T> = core::result::Result<T, Error>;

impl Error {
    pub const fn out_of_bounds() -> Self {
        Self::OutOfBounds
    }

    pub const fn unexpected_input() -> Self {
        Self::UnexpectedInput
    }

    pub const fn not_ready() -> Self {
        Self::NotReady
    }

    pub const fn malformed_data() -> Self {
        Self::MalformedData
    }

    pub const fn invalid_digest() -> Self {
        Self::InvalidDigest
    }

    pub const fn insufficient_buffer() -> Self {
        Self::InsufficientBuffer
    }

    pub const fn crypto_error() -> Self {
        Self::CryptoError
    }
}

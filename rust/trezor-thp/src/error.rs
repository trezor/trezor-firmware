/// Payload of `transport_error` message type (0x42).
#[cfg_attr(any(test, debug_assertions), derive(Debug))]
#[derive(Clone, Copy, PartialEq, Eq)]
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
        matches!(self, TransportError::TransportBusy)
    }

    pub fn as_str(&self) -> &'static str {
        match self {
            TransportError::TransportBusy => "TRANSPORT_BUSY",
            TransportError::UnallocatedChannel => "UNALLOCATED_CHANNEL",
            TransportError::DecryptionFailed => "DECRYPTION_FAILED",
            TransportError::DeviceLocked => "DEVICE_LOCKED",
        }
    }
}

impl From<TransportError> for u8 {
    fn from(val: TransportError) -> u8 {
        val as u8
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
            _ => return Err(Error::malformed_data()),
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
#[derive(Clone, Copy, PartialEq, Eq)]
pub enum Error {
    /// Invalid data/operation from crate user.
    UnexpectedInput,
    /// Channel is not ready to send another message, or there is no message ready to be passed
    /// to the caller.
    NotReady,
    /// Invalid data from the wire.
    MalformedData,
    /// Checksum doesn't match.
    InvalidChecksum,
    /// Provided buffer is too small.
    InsufficientBuffer,
    /// Secure channel cryptography failed.
    CryptoError,
}

#[cfg(feature = "trezor_noise_protocol")]
impl From<trezor_noise_protocol::Error> for Error {
    fn from(val: trezor_noise_protocol::Error) -> Self {
        match val.kind() {
            trezor_noise_protocol::ErrorKind::DH | trezor_noise_protocol::ErrorKind::Decryption => {
                Self::crypto_error()
            }
            trezor_noise_protocol::ErrorKind::TooShort => Self::malformed_data(),
        }
    }
}

#[cfg(feature = "noise_protocol")]
impl From<noise_protocol::Error> for Error {
    fn from(val: noise_protocol::Error) -> Self {
        match val.kind() {
            noise_protocol::ErrorKind::DH | noise_protocol::ErrorKind::Decryption => {
                Self::crypto_error()
            }
            noise_protocol::ErrorKind::TooShort => Self::malformed_data(),
            noise_protocol::ErrorKind::NeedPSK => unreachable!(),
        }
    }
}

pub type Result<T> = core::result::Result<T, Error>;

impl Error {
    pub const fn unexpected_input() -> Self {
        Self::UnexpectedInput
    }

    pub const fn not_ready() -> Self {
        Self::NotReady
    }

    pub const fn malformed_data() -> Self {
        Self::MalformedData
    }

    pub const fn invalid_checksum() -> Self {
        Self::InvalidChecksum
    }

    pub const fn insufficient_buffer() -> Self {
        Self::InsufficientBuffer
    }

    pub const fn crypto_error() -> Self {
        Self::CryptoError
    }
}

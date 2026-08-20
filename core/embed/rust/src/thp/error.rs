use trezor_thp::Error as ThpError;

use crate::micropython::exception::{builtin, Exception, ExceptionType};
use crate::micropython::qstr::Qstr;

#[cfg_attr(test, derive(Debug))]
pub(super) enum Error {
    Protocol(ThpError),
    CannotUnlock,
    ChannelNotFound,
    InterfaceNotFound,
    TooManyInterfaces,
    UnexpectedPacketInResult,
    InvalidKeyLength,
}

pub(super) static THP_EXCEPTION_TYPE: ExceptionType =
    ExceptionType::new(builtin::Exception, Qstr::MP_QSTR_ThpError);

fn thp_exception_str(error: ThpError) -> &'static str {
    match error {
        ThpError::UnexpectedInput => "Unexpected input",
        ThpError::NotReady => "Not ready",
        ThpError::MalformedData => "Malformed data",
        ThpError::CryptoError => "Crypto error",
        ThpError::InvalidChecksum => "Invalid checksum",
        ThpError::InsufficientBuffer => "Insufficient buffer",
    }
}

impl Error {
    pub fn into_exception(self) -> Exception {
        let error_str = match self {
            Error::Protocol(error) => thp_exception_str(error),
            Error::CannotUnlock => "THP context is locked",
            Error::ChannelNotFound => "Channel not found",
            Error::InterfaceNotFound => "Interface not found",
            Error::TooManyInterfaces => "Too many interfaces",
            Error::UnexpectedPacketInResult => "Unexpected packet in result",
            Error::InvalidKeyLength => "Invalid key length",
        };
        Exception::new_with_arg(&THP_EXCEPTION_TYPE, error_str)
    }
}

impl From<ThpError> for Error {
    fn from(error: ThpError) -> Self {
        Error::Protocol(error)
    }
}

impl From<Error> for crate::micropython::error::Error {
    fn from(error: Error) -> Self {
        crate::micropython::error::Error::Exception(error.into_exception())
    }
}

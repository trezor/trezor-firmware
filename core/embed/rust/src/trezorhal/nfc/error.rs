use rtl::error::Error as RtlError;

#[derive(ufmt::derive::uDebug)]
pub enum NfcError {
    /// Invalid parameters provided by the application.
    UnexpectedInput,
    /// Invalid data originating from the NFC interface.
    InvalidData,
    /// Unsupported tag type.
    UnsupportedTag,
    /// Secure channel failure.
    CryptoError,
    /// Failed to validate certificate provided by the tag.
    InvalidCertificate,
    /// Tag disappeared before operation completed.
    TagDisconnected,
    /// Received Response-APDU with unsuccessful status code.
    CommandFailed(u16),
    /// Driver returned an error.
    DriverError(RtlError),
}

impl From<RtlError> for NfcError {
    fn from(rtl_error: RtlError) -> Self {
        match rtl_error {
            RtlError::ENOEN => NfcError::TagDisconnected,
            e => NfcError::DriverError(e),
        }
    }
}

#[cfg(feature = "micropython")]
pub mod micropython {
    use super::super::apdu::StatusWord;
    use super::*;
    use crate::micropython::exception::{builtin, Exception, ExceptionType};
    use crate::micropython::qstr::Qstr;
    use crate::micropython::{Error, Obj};

    pub(crate) static EXCEPTION_TYPE: ExceptionType =
        ExceptionType::new(builtin::RuntimeError, Qstr::MP_QSTR_NfcError);
    pub(crate) static EXCEPTION_COMMAND_FAILED_TYPE: ExceptionType =
        ExceptionType::new(&EXCEPTION_TYPE, Qstr::MP_QSTR_NfcCommandFailed);

    fn code_description(code: u16) -> Obj {
        match StatusWord::try_from(code) {
            Ok(sw) => {
                let msg = uformat!(len: 32, "{:?}", sw);
                msg.as_str().try_into().unwrap_or(Obj::const_none())
            }
            Err(_) => Obj::const_none(),
        }
    }

    impl From<NfcError> for Error {
        fn from(error: NfcError) -> Self {
            let exc = |msg| Error::Exception(Exception::new_with_arg(&EXCEPTION_TYPE, msg));
            match error {
                NfcError::UnexpectedInput => exc(c"Unexpected input"),
                NfcError::InvalidData => exc(c"Malformed NFC data"),
                NfcError::UnsupportedTag => exc(c"Unsupported tag type"),
                NfcError::CryptoError => exc(c"Secure channel failed"),
                NfcError::InvalidCertificate => exc(c"Certificate validation failed"),
                NfcError::TagDisconnected => Error::EOFError,
                NfcError::CommandFailed(code) => Error::Exception(Exception::new(
                    &EXCEPTION_COMMAND_FAILED_TYPE,
                    &[code.into(), code_description(code)],
                )),
                NfcError::DriverError(e) => Error::OSError(e),
            }
        }
    }
}

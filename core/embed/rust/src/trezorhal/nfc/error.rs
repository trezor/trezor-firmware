use rtl::error::Error as RtlError;

#[derive(ufmt::derive::uDebug)]
pub enum NfcError {
    InvalidData,
    UnsupportedTag,
    CryptoError,
    InvalidCertificate,
    TagDisconnected,
    CommandFailed(u16),
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
                NfcError::InvalidData => exc(c"Malformed NFC data"),
                NfcError::UnsupportedTag => exc(c"Unsupported tag type"),
                // FIXME NfcError::CryptoError => exc(c"Secure channel failed"),
                NfcError::CryptoError => Error::Exception(Exception::new(
                    &EXCEPTION_COMMAND_FAILED_TYPE,
                    &[Obj::small_int(0x1337), Obj::const_none()],
                )),
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

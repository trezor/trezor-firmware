use rtl::error::Error as RtlError;

use super::apdu::StatusWord;

#[derive(ufmt::derive::uDebug)]
pub enum NfcError {
    DriverError(RtlError),
    InvalidData,
    TimedOut,
    UnsupportedTag,
    CommandFailed(u16),
    HandshakeFailed,
    TagDisconnected,
}

impl From<RtlError> for NfcError {
    fn from(e: RtlError) -> Self {
        NfcError::DriverError(e)
    }
}

#[cfg(feature = "micropython")]
mod micropython {
    use num_traits::FromPrimitive;

    use super::*;
    use crate::micropython::exception::{builtin, Exception, ExceptionType};
    use crate::micropython::qstr::Qstr;
    use crate::micropython::{Error, Obj};

    pub(super) static EXCEPTION_TYPE: ExceptionType =
        ExceptionType::new(builtin::Exception, Qstr::MP_QSTR_NfcError); // TODO: RuntimeError base?

    impl From<NfcError> for Error {
        fn from(error: NfcError) -> Self {
            fn exc(arg: impl TryInto<Obj>) -> Error {
                Error::Exception(Exception::new_with_arg(&EXCEPTION_TYPE, arg))
            }
            match error {
                NfcError::DriverError(e) => Error::OSError(e),
                NfcError::InvalidData => exc(c"Malformed NFC data"),
                NfcError::TimedOut => exc(c"NFC operation timed out"),
                NfcError::UnsupportedTag => exc(c"Unsupported tag type"),
                NfcError::CommandFailed(code) => match StatusWord::from_u16(code) {
                    Some(sw) => {
                        let msg = uformat!("Command failed: {:?}", sw);
                        exc(msg.as_str())
                    }
                    None => {
                        let bytes = code.to_be_bytes();
                        let msg = uformat!("Command failed: {}", crate::strutil::hex_bytes(&bytes));
                        exc(msg.as_str())
                    }
                },

                NfcError::HandshakeFailed => exc(c"Handshake failed"),
                NfcError::TagDisconnected => exc(c"Tag disconnected"), /* TODO: maybe map to
                                                                        * EOFError */
            }
        }
    }
}

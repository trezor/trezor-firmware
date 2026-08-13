use core::convert::{Infallible, TryInto};
use core::ffi::CStr;
use core::num::TryFromIntError;

use super::exception::{builtin, Exception};
use super::obj::Obj;

#[allow(clippy::enum_variant_names)] // We mimic the Python exception classnames here.
#[derive(Debug)]
pub enum Error {
    TypeError,
    OutOfRange,
    MissingKwargs,
    AllocationFailed,
    EOFError,
    IndexError,
    KeyError(Obj),
    AttributeError(Obj),
    ValueError(&'static CStr),
    ValueErrorParam(&'static CStr, Obj),
    RuntimeError(&'static CStr),
    NotImplementedError,
    Exception(Exception),
}

impl Error {
    /// Create an exception instance matching the error code.
    pub fn into_exception(self) -> Exception {
        match self {
            Error::TypeError => Exception::new(&builtin::TypeError, &[]),
            Error::OutOfRange => Exception::new(&builtin::OverflowError, &[]),
            Error::MissingKwargs => Exception::new(&builtin::TypeError, &[]),
            Error::AllocationFailed => Exception::new(&builtin::MemoryError, &[]),
            Error::IndexError => Exception::new(&builtin::IndexError, &[]),
            Error::KeyError(key) => Exception::new_with_arg(&builtin::KeyError, key),
            Error::ValueError(msg) => Exception::new_with_arg(&builtin::ValueError, msg),
            Error::ValueErrorParam(msg, param) => {
                let args: &[Obj] = match msg.try_into() {
                    Ok(msg) => &[msg, param],
                    Err(_) => &[],
                };
                Exception::new(&builtin::ValueError, args)
            }
            Error::AttributeError(attr) => Exception::new_with_arg(&builtin::AttributeError, attr),
            Error::EOFError => Exception::new(&builtin::EOFError, &[]),
            Error::RuntimeError(msg) => Exception::new_with_arg(&builtin::RuntimeError, msg),
            Error::NotImplementedError => Exception::new(&builtin::NotImplementedError, &[]),
            Error::Exception(exception) => exception,
        }
    }
}

// Implements a conversion from `core::convert::Infallible` to `Error` to so
// that code generic over `TryFrom` can work with values covered by the blanket
// impl for `Into`: `https://doc.rust-lang.org/std/convert/enum.Infallible.html`
impl From<Infallible> for Error {
    fn from(_: Infallible) -> Self {
        unreachable!()
    }
}

impl From<TryFromIntError> for Error {
    fn from(_: TryFromIntError) -> Self {
        Self::OutOfRange
    }
}

// #[cfg(feature = "thp")]
// impl From<trezor_thp::Error> for Error {
//     fn from(error: trezor_thp::Error) -> Self {
//         match error {
//             trezor_thp::Error::UnexpectedInput =>
// Error::ThpError(c"Unexpected input"),             trezor_thp::Error::NotReady
// => Error::ThpError(c"Not ready"),
// trezor_thp::Error::MalformedData => Error::ThpError(c"Malformed data"),
//             trezor_thp::Error::InvalidChecksum => Error::ThpError(c"Invalid
// checksum"),             trezor_thp::Error::InsufficientBuffer =>
// Error::ThpError(c"Insufficient buffer"),
// trezor_thp::Error::CryptoError => Error::ThpError(c"Crypto error"),         }
//     }
// }

// #[cfg(feature = "crypto")]
// impl From<crypto::Error> for crate::error::Error {
//     fn from(e: crypto::Error) -> Self {
//         match e {
//             crypto::Error::SignatureVerificationFailed => {
//                 value_error!(c"Signature verification failed")
//             }
//             crypto::Error::InvalidEncoding => value_error!(c"Invalid key or
// signature encoding"),             crypto::Error::InvalidParams =>
// value_error!(c"Invalid cryptographic parameters"),
// crypto::Error::InvalidContext => value_error!(c"Invalid cryptographic
// context"),             crypto::Error::AuthenticationFailed =>
// value_error!(c"Authentication failed"),
// crypto::Error::InvalidSigmask => value_error!(c"Invalid sigmask"),         }
//     }
// }

use core::{convert::Infallible, ffi::CStr, num::TryFromIntError};

#[cfg(feature = "micropython")]
use {
    crate::micropython::{
        exception::{self, new_exception, new_exception_arg_from, new_exception_args},
        obj::Obj,
        qstr::Qstr,
    },
    core::convert::TryInto,
};

#[cfg(feature = "thp")]
use crate::thp::micropython::ThpError;

#[allow(clippy::enum_variant_names)] // We mimic the Python exception classnames here.
#[derive(Clone, Copy, Debug)]
pub enum Error {
    TypeError,
    OutOfRange,
    MissingKwargs,
    AllocationFailed,
    EOFError,
    IndexError,
    #[cfg(feature = "micropython")]
    CaughtException(Obj),
    #[cfg(feature = "micropython")]
    KeyError(Obj),
    #[cfg(feature = "micropython")]
    AttributeError(Qstr),
    ValueError(&'static CStr),
    #[cfg(feature = "micropython")]
    ValueErrorParam(&'static CStr, Obj),
    RuntimeError(&'static CStr),
    NotImplementedError,
    #[cfg(feature = "thp")]
    ThpError(&'static CStr),
}

#[allow(unused_macros)]
macro_rules! value_error {
    ($msg:expr) => {
        $crate::error::Error::ValueError($msg)
    };
}

#[allow(unused_imports)]
pub(crate) use value_error;

#[cfg(feature = "micropython")]
impl Error {
    /// Create an exception instance matching the error code. The result of this
    /// call should only be used to immediately raise the exception, because the
    /// object is not guaranteed to remain intact. MicroPython might reuse the
    /// same space for creating a different exception.
    pub unsafe fn into_obj(self) -> Obj {
        unsafe {
            // SAFETY: First argument is a reference to a valid exception type.
            // EXCEPTION: Sensibly, `new_exception_*` does not raise.
            match self {
                Error::TypeError => new_exception(exception::TypeError),
                Error::OutOfRange => new_exception(exception::OverflowError),
                Error::MissingKwargs => new_exception(exception::TypeError),
                Error::AllocationFailed => new_exception(exception::MemoryError),
                Error::IndexError => new_exception(exception::IndexError),
                Error::CaughtException(obj) => obj,
                Error::KeyError(key) => new_exception_arg_from(exception::KeyError, key),
                Error::ValueError(msg) => new_exception_arg_from(exception::ValueError, msg),
                Error::ValueErrorParam(msg, param) => match msg.try_into() {
                    Ok(msg) => new_exception_args(exception::ValueError, &[msg, param]),
                    _ => new_exception(exception::ValueError),
                },
                Error::AttributeError(attr) => {
                    new_exception_arg_from(exception::AttributeError, attr)
                }
                Error::EOFError => new_exception(exception::EOFError),
                Error::RuntimeError(msg) => new_exception_arg_from(exception::RuntimeError, msg),
                Error::NotImplementedError => new_exception(exception::NotImplementedError),
                #[cfg(feature = "thp")]
                Error::ThpError(msg) => new_exception_arg_from(&ThpError, msg),
            }
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

#[cfg(feature = "thp")]
impl From<trezor_thp::Error> for Error {
    fn from(error: trezor_thp::Error) -> Self {
        match error {
            trezor_thp::Error::UnexpectedInput => Error::ThpError(c"Unexpected input"),
            trezor_thp::Error::NotReady => Error::ThpError(c"Not ready"),
            trezor_thp::Error::MalformedData => Error::ThpError(c"Malformed data"),
            trezor_thp::Error::InvalidChecksum => Error::ThpError(c"Invalid checksum"),
            trezor_thp::Error::InsufficientBuffer => Error::ThpError(c"Insufficient buffer"),
            trezor_thp::Error::CryptoError => Error::ThpError(c"Crypto error"),
        }
    }
}

#[cfg(feature = "crypto")]
impl From<crypto::Error> for crate::error::Error {
    fn from(e: crypto::Error) -> Self {
        match e {
            crypto::Error::SignatureVerificationFailed => {
                value_error!(c"Signature verification failed")
            }
            crypto::Error::InvalidEncoding => value_error!(c"Invalid key or signature encoding"),
            crypto::Error::InvalidParams => value_error!(c"Invalid cryptographic parameters"),
            crypto::Error::InvalidContext => value_error!(c"Invalid cryptographic context"),
            crypto::Error::AuthenticationFailed => value_error!(c"Authentication failed"),
            crypto::Error::InvalidSigmask => value_error!(c"Invalid sigmask"),
        }
    }
}

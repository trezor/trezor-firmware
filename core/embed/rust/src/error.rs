use core::{convert::Infallible, num::TryFromIntError};
use cstr_core::CStr;

#[cfg(feature = "micropython")]
use {
    crate::micropython::{ffi, obj::Obj, qstr::Qstr},
    core::convert::TryInto,
};

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
}

#[macro_export]
macro_rules! value_error {
    ($msg:expr) => {
        $crate::error::Error::ValueError(cstr_core::cstr!($msg))
    };
}

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
                Error::TypeError => ffi::mp_obj_new_exception(&ffi::mp_type_TypeError),
                Error::OutOfRange => ffi::mp_obj_new_exception(&ffi::mp_type_OverflowError),
                Error::MissingKwargs => ffi::mp_obj_new_exception(&ffi::mp_type_TypeError),
                Error::AllocationFailed => ffi::mp_obj_new_exception(&ffi::mp_type_MemoryError),
                Error::IndexError => ffi::mp_obj_new_exception(&ffi::mp_type_IndexError),
                Error::CaughtException(obj) => obj,
                Error::KeyError(key) => {
                    ffi::mp_obj_new_exception_args(&ffi::mp_type_KeyError, 1, &key)
                }
                Error::ValueError(msg) => {
                    if let Ok(msg) = msg.try_into() {
                        ffi::mp_obj_new_exception_args(&ffi::mp_type_ValueError, 1, &msg)
                    } else {
                        ffi::mp_obj_new_exception(&ffi::mp_type_ValueError)
                    }
                }
                Error::ValueErrorParam(msg, param) => {
                    if let Ok(msg) = msg.try_into() {
                        let args = [msg, param];
                        ffi::mp_obj_new_exception_args(&ffi::mp_type_ValueError, 2, args.as_ptr())
                    } else {
                        ffi::mp_obj_new_exception(&ffi::mp_type_ValueError)
                    }
                }
                Error::AttributeError(attr) => {
                    ffi::mp_obj_new_exception_args(&ffi::mp_type_AttributeError, 1, &attr.into())
                }
                Error::EOFError => ffi::mp_obj_new_exception(&ffi::mp_type_EOFError),
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

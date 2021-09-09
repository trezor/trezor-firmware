use core::convert::{Infallible, TryInto};
use cstr_core::CStr;

use crate::micropython::{ffi, obj::Obj, qstr::Qstr};

#[derive(Debug)]
pub enum Error {
    TypeError,
    OutOfRange,
    MissingKwargs,
    AllocationFailed,
    CaughtException(Obj),
    KeyError(Obj),
    AttributeError(Qstr),
    ValueError(&'static CStr),
    ValueErrorParam(&'static CStr, Obj),
}

impl Error {
    /// Create an exception instance matching the error code.
    /// The result of this call should only be used to immediately raise the
    /// exception, because the object is not guaranteed to remain intact.
    /// Micropython might reuse the same space for creating a different
    /// exception.
    pub unsafe fn to_obj(self) -> Obj {
        unsafe {
            // SAFETY:
            // - first argument is a reference to a valid exception type
            // EXCEPTION: Sensibly, `new_exception_*` does not raise.
            match self {
                Error::TypeError => ffi::mp_obj_new_exception(&ffi::mp_type_TypeError),
                Error::OutOfRange => ffi::mp_obj_new_exception(&ffi::mp_type_OverflowError),
                Error::MissingKwargs => ffi::mp_obj_new_exception(&ffi::mp_type_TypeError),
                Error::AllocationFailed => ffi::mp_obj_new_exception(&ffi::mp_type_MemoryError),
                Error::CaughtException(obj) => obj,
                Error::KeyError(key) => {
                    ffi::mp_obj_new_exception_arg1(&ffi::mp_type_KeyError, key.into())
                }
                Error::ValueError(msg) => {
                    ffi::mp_obj_new_exception_msg(&ffi::mp_type_ValueError, msg.as_ptr())
                }
                Error::ValueErrorParam(msg, param) => {
                    if let Ok(msg) = msg.try_into() {
                        let args: [Obj; 2] = [msg, param.into()];
                        ffi::mp_obj_new_exception_args(&ffi::mp_type_ValueError, 2, args.as_ptr())
                    } else {
                        ffi::mp_obj_new_exception(&ffi::mp_type_ValueError)
                    }
                }
                Error::AttributeError(attr) => {
                    ffi::mp_obj_new_exception_arg1(&ffi::mp_type_AttributeError, attr.into())
                }
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

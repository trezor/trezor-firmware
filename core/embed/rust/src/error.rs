// Copyright (c) 2025 Trezor Company s.r.o.
//
// Permission is hereby granted, free of charge, to any person obtaining a copy
// of this software and associated documentation files (the "Software"), to deal
// in the Software without restriction, including without limitation the rights
// to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
// copies of the Software, and to permit persons to whom the Software is
// furnished to do so, subject to the following conditions:
//
// The above copyright notice and this permission notice shall be included in
// all copies or substantial portions of the Software.
//
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
// AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
// LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
// OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
// SOFTWARE.

use core::{convert::Infallible, ffi::CStr, num::TryFromIntError};

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
    RuntimeError(&'static CStr),
}

macro_rules! value_error {
    ($msg:expr) => {
        $crate::error::Error::ValueError($msg)
    };
}

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
                Error::RuntimeError(msg) => {
                    if let Ok(msg) = msg.try_into() {
                        ffi::mp_obj_new_exception_args(&ffi::mp_type_RuntimeError, 1, &msg)
                    } else {
                        ffi::mp_obj_new_exception(&ffi::mp_type_RuntimeError)
                    }
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

impl From<TryFromIntError> for Error {
    fn from(_: TryFromIntError) -> Self {
        Self::OutOfRange
    }
}

use cstr_core::CStr;

use crate::{error::Error, micropython::qstr::Qstr};

// XXX const version of `from_bytes_with_nul_unchecked` is nightly-only.

pub fn experimental_not_enabled() -> Error {
    let msg =
        unsafe { CStr::from_bytes_with_nul_unchecked(b"Experimental features are disabled.\0") };
    Error::ValueError(msg)
}

pub fn unknown_field_type() -> Error {
    let msg = unsafe { CStr::from_bytes_with_nul_unchecked(b"Unknown field type.\0") };
    Error::ValueError(msg)
}

pub fn missing_required_field(field: Qstr) -> Error {
    let msg = unsafe { CStr::from_bytes_with_nul_unchecked(b"Missing required field\0") };
    Error::ValueErrorParam(msg, field.into())
}

pub fn invalid_value(field: Qstr) -> Error {
    let msg = unsafe { CStr::from_bytes_with_nul_unchecked(b"Invalid value for field\0") };
    Error::ValueErrorParam(msg, field.into())
}

pub fn end_of_buffer() -> Error {
    let msg = unsafe { CStr::from_bytes_with_nul_unchecked(b"End of buffer.\0") };
    Error::ValueError(msg)
}

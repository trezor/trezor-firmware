use cstr_core::cstr;

use crate::{error::Error, micropython::qstr::Qstr};

// XXX const version of `from_bytes_with_nul_unchecked` is nightly-only.

pub fn experimental_not_enabled() -> Error {
    let msg = cstr!("Experimental features are disabled");
    Error::ValueError(msg)
}

pub fn unknown_field_type() -> Error {
    let msg = cstr!("Unknown field type");
    Error::ValueError(msg)
}

pub fn missing_required_field(field: Qstr) -> Error {
    let msg = cstr!("Missing required field");
    Error::ValueErrorParam(msg, field.into())
}

pub fn invalid_value(field: Qstr) -> Error {
    let msg = cstr!("Invalid value for field");
    Error::ValueErrorParam(msg, field.into())
}

pub fn end_of_buffer() -> Error {
    let msg = cstr!("End of buffer");
    Error::ValueError(msg)
}

use cstr_core::cstr;

use crate::{error::Error, micropython::qstr::Qstr};

// XXX const version of `from_bytes_with_nul_unchecked` is nightly-only.

pub fn experimental_not_enabled() -> Error {
    value_error!("Experimental features are disabled.")
}

pub fn unknown_field_type() -> Error {
    value_error!("Unknown field type.")
}

pub fn missing_required_field(field: Qstr) -> Error {
    Error::ValueErrorParam(cstr!("Missing required field."), field.into())
}

pub fn invalid_value(field: Qstr) -> Error {
    Error::ValueErrorParam(cstr!("Invalid value for field."), field.into())
}

pub fn end_of_buffer() -> Error {
    value_error!("End of buffer.")
}

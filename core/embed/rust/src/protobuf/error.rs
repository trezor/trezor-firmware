use cstr_core::cstr;

use crate::{error::Error, micropython::qstr::Qstr};

pub const fn experimental_not_enabled() -> Error {
    value_error!("Experimental features are disabled.")
}

pub const fn unknown_field_type() -> Error {
    value_error!("Unknown field type.")
}

pub fn missing_required_field(field: Qstr) -> Error {
    Error::ValueErrorParam(cstr!("Missing required field."), field.into())
}

pub fn invalid_value(field: Qstr) -> Error {
    Error::ValueErrorParam(cstr!("Invalid value for field."), field.into())
}

pub const fn end_of_buffer() -> Error {
    value_error!("End of buffer.")
}

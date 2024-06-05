use crate::{
    error::{value_error, Error},
    micropython::qstr::Qstr,
};

pub const fn experimental_not_enabled() -> Error {
    value_error!(c"Experimental features are disabled.")
}

pub const fn unknown_field_type() -> Error {
    value_error!(c"Unknown field type.")
}

pub fn missing_required_field(field: Qstr) -> Error {
    Error::ValueErrorParam(c"Missing required field.", field.into())
}

pub fn invalid_value(field: Qstr) -> Error {
    Error::ValueErrorParam(c"Invalid value for field.", field.into())
}

pub const fn end_of_buffer() -> Error {
    value_error!(c"End of buffer.")
}

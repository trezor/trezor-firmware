use crate::micropython::{error::Error, qstr::Attribute};

pub const fn experimental_not_enabled() -> Error {
    Error::ValueError(c"Experimental features are disabled.")
}

pub const fn unknown_field_type() -> Error {
    Error::ValueError(c"Unknown field type.")
}

pub const fn missing_required_field(field: Attribute) -> Error {
    Error::ValueErrorParam(c"Missing required field.", field.to_obj())
}

pub const fn invalid_value(field: Attribute) -> Error {
    Error::ValueErrorParam(c"Invalid value for field.", field.to_obj())
}

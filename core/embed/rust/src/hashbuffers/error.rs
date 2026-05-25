use core::{convert::Infallible, ffi::CStr};
use micropython::qstr::Attribute;

pub struct Error(micropython::Error);

impl Error {
    pub const fn value_error(message: &'static CStr) -> Self {
        Error(micropython::Error::ValueError(message))
    }
}

impl From<Error> for micropython::Error {
    fn from(error: Error) -> Self {
        error.0
    }
}

impl From<Infallible> for Error {
    fn from(_: Infallible) -> Self {
        unreachable!()
    }
}

impl From<micropython::Error> for Error {
    fn from(error: micropython::Error) -> Self {
        Error(error)
    }
}

pub const fn experimental_not_enabled() -> Error {
    Error(micropython::Error::ValueError(
        c"Experimental features are disabled.",
    ))
}

pub const fn unknown_field_type() -> Error {
    Error(micropython::Error::ValueError(c"Unknown field type."))
}

pub const fn missing_required_field(field: Attribute) -> Error {
    Error(micropython::Error::ValueErrorParam(
        c"Missing required field.",
        field.to_obj(),
    ))
}

pub const fn invalid_value(field: Attribute) -> Error {
    Error(micropython::Error::ValueErrorParam(
        c"Invalid value for field.",
        field.to_obj(),
    ))
}

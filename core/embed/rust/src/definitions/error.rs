const INVALID_DEFINITION_STR: &str = "Invalid definition";
const INVALID_SIGNATURE_STR: &str = "Invalid definition signature";

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Error {
    InvalidDefinition,
    InvalidSignature,
    UnsupportedVersion,
    NotEnoughData,
    BadMagic,
    UnexpectedType,
    Outdated,
    InvalidAlignment,
    TrailingData,
    InvalidPayload,
}

impl From<crate::io::Error> for Error {
    fn from(error: crate::io::Error) -> Self {
        match error {
            crate::io::Error::EOFError => Error::NotEnoughData,
        }
    }
}

impl Error {
    pub fn to_string(self) -> &'static str {
        match self {
            Error::InvalidDefinition => INVALID_DEFINITION_STR,
            Error::InvalidSignature => INVALID_SIGNATURE_STR,
            Error::UnsupportedVersion => "Unsupported definition format version",
            Error::NotEnoughData => INVALID_DEFINITION_STR,
            Error::BadMagic => INVALID_DEFINITION_STR,
            Error::UnexpectedType => "Definition type mismatch",
            Error::Outdated => "Definition is outdated",
            Error::InvalidAlignment => INVALID_DEFINITION_STR,
            Error::TrailingData => INVALID_DEFINITION_STR,
            Error::InvalidPayload => INVALID_DEFINITION_STR,
        }
    }
}

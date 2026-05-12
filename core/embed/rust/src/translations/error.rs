const INVALID_TRANSLATIONS_BLOB: &str = "Invalid translations blob";

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Error {
    InvalidOffsetTable,
    InvalidAlignment,
    InvalidLength,
    InvalidString,
    TrailingData,
    NotEnoughData,
    InvalidDataHash,
    BadMagic,
    InvalidSignature,
    TranslationsInUse,
    WriteFailed,
}

impl From<crate::io::Error> for Error {
    fn from(error: crate::io::Error) -> Self {
        match error {
            crate::io::Error::EOFError => Error::NotEnoughData,
        }
    }
}

impl From<core::str::Utf8Error> for Error {
    fn from(_: core::str::Utf8Error) -> Self {
        Error::InvalidString
    }
}

impl Error {
    pub fn to_string(&self) -> &str {
        match self {
            Error::InvalidString => INVALID_TRANSLATIONS_BLOB,
            Error::TranslationsInUse => "Translations in use",
            Error::InvalidOffsetTable => INVALID_TRANSLATIONS_BLOB,
            Error::InvalidAlignment => INVALID_TRANSLATIONS_BLOB,
            Error::InvalidLength => INVALID_TRANSLATIONS_BLOB,
            Error::TrailingData => INVALID_TRANSLATIONS_BLOB,
            Error::NotEnoughData => INVALID_TRANSLATIONS_BLOB,
            Error::InvalidDataHash => INVALID_TRANSLATIONS_BLOB,
            Error::InvalidSignature => "Invalid signature",
            Error::BadMagic => "Unknown translations blob version",
            Error::WriteFailed => "Failed to write translations blob",
        }
    }
}

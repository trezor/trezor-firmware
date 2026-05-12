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

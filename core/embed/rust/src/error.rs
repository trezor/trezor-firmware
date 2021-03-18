use core::convert::Infallible;
use core::fmt;

use cstr_core::CStr;

pub enum Error {
    Missing,
    OutOfRange,
    InvalidType,
    NotBuffer,
    NotInt,
}

impl Error {
    pub fn as_cstr(&self) -> &'static CStr {
        // SAFETY: Safe because we are passing in \0-terminated literals.
        unsafe {
            let cstr = |s: &'static str| CStr::from_bytes_with_nul_unchecked(s.as_bytes());
            match self {
                Error::Missing => cstr("Missing\0"),
                Error::OutOfRange => cstr("OutOfRange\0"),
                Error::InvalidType => cstr("InvalidType\0"),
                Error::NotBuffer => cstr("NotBuffer\0"),
                Error::NotInt => cstr("NotInt\0"),
            }
        }
    }
}

impl Into<&'static CStr> for Error {
    fn into(self) -> &'static CStr {
        self.as_cstr()
    }
}

impl fmt::Debug for Error {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        self.as_cstr().fmt(f)
    }
}

impl From<Infallible> for Error {
    fn from(_: Infallible) -> Self {
        unreachable!()
    }
}

use core::fmt::Debug;

pub enum Error {
    Missing,
    OutOfRange,
    NotBuffer,
    NotInt,
}

impl Debug for Error {
    fn fmt(&self, f: &mut core::fmt::Formatter<'_>) -> core::fmt::Result {
        match self {
            Error::Missing => f.write_str("Missing"),
            Error::OutOfRange => f.write_str("OutOfRange"),
            Error::NotBuffer => f.write_str("NotBuffer"),
            Error::NotInt => f.write_str("NotInt"),
        }
    }
}

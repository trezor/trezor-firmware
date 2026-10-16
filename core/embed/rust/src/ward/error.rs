use crate::micropython::error::Error as MpyError;
use crate::micropython::exception::{builtin, Exception, ExceptionType};
use crate::micropython::qstr::Qstr;

pub(super) static WARD_EXCEPTION_TYPE: ExceptionType =
    ExceptionType::new(builtin::Exception, Qstr::MP_QSTR_WardError);

#[cfg_attr(test, derive(Debug, PartialEq))]
pub(super) enum Error {
    InvalidWalletId,
    Locked,
    TooLarge,
    Full,
    Storage,
}

impl From<Error> for MpyError {
    fn from(error: Error) -> Self {
        let msg = match error {
            Error::InvalidWalletId => return MpyError::ValueError(c"Invalid wallet id"),
            Error::Locked => "Storage is locked",
            Error::TooLarge => "Record is too large",
            Error::Full => "Store is full",
            Error::Storage => "Storage failure",
        };
        MpyError::Exception(Exception::new_with_arg(&WARD_EXCEPTION_TYPE, msg))
    }
}

use crate::micropython::exception::{builtin, ExceptionType};
use crate::micropython::qstr::Qstr;

pub(super) static WARD_EXCEPTION_TYPE: ExceptionType =
    ExceptionType::new(builtin::Exception, Qstr::MP_QSTR_WardError);

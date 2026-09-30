use core::ffi::CStr;

pub use ffi::ts_t;
use num_derive::FromPrimitive;
use num_traits::FromPrimitive;

use super::ffi;

pub type TStatus = ts_t;

impl TStatus {
    const fn code(&self) -> i32 {
        self.code
    }

    pub const fn is_ok(&self) -> bool {
        self.code() == 0
    }

    pub fn ok(&self) -> Result<(), Error> {
        if self.is_ok() {
            return Ok(());
        }
        match Error::from_i32(self.code()) {
            Some(e) => Err(e),
            // TODO: consider something nonfatal
            None => fatal_error!("unknown ts_t value"),
        }
    }

    pub fn map_err<E>(&self, func: impl FnOnce(Error) -> E) -> Result<(), E> {
        self.ok().map_err(func)
    }

    pub const fn from_error(e: Error) -> Self {
        Self { code: e as i32 }
    }
}

// Must be kept in sync with the values in error_handling.h.
#[derive(Copy, Clone, FromPrimitive)]
#[repr(i32)]
pub enum Error {
    // Standard errno
    EINVAL = ffi::EINVAL,
    ENOMEM = ffi::ENOMEM,
    ENOENT = ffi::ENOENT,
    EBUSY = ffi::EBUSY,
    ETIMEDOUT = ffi::ETIMEDOUT,
    EIO = ffi::EIO,
    EBADMSG = ffi::EBADMSG,
    EACCES = ffi::EACCES,
    EEXIST = ffi::EEXIST,
    // Trezor-specific
    ENOINIT = 2000,  //< Not initialized
    ENOEN = 2001,    //< Not enabled
    ENOSTATE = 2002, //< Wrong state
}

impl Error {
    pub fn to_str(self) -> &'static str {
        let ts = TStatus::from_error(self);
        // SAFETY: ffi
        let ptr = unsafe { ffi::ts_string(ts) };
        // SAFETY: TODO
        let cstr = unsafe { CStr::from_ptr(ptr) };
        cstr.to_str().unwrap_or("?ERROR")
    }
}

impl From<Error> for i32 {
    fn from(e: Error) -> Self {
        e as i32
    }
}

pub trait UnwrapOrFatalError<T> {
    fn unwrap_or_fatal_error(self, msg: &str, file: &str, line: u32) -> T;
}

impl<T> UnwrapOrFatalError<T> for Option<T> {
    fn unwrap_or_fatal_error(self, msg: &str, file: &str, line: u32) -> T {
        match self {
            Some(x) => x,
            None => crate::sysexit::system_exit_fatal(msg, file, line),
        }
    }
}

impl<T, E> UnwrapOrFatalError<T> for Result<T, E> {
    fn unwrap_or_fatal_error(self, msg: &str, file: &str, line: u32) -> T {
        match self {
            Ok(x) => x,
            Err(_) => crate::sysexit::system_exit_fatal(msg, file, line),
        }
    }
}

#[macro_export]
macro_rules! unwrap {
    ($e:expr, $msg:expr) => {{
        use $crate::error::UnwrapOrFatalError;
        $e.unwrap_or_fatal_error($msg, file!(), line!())
    }};
    ($expr:expr) => {
        unwrap!($expr, "unwrap failed")
    };
}

#[macro_export]
macro_rules! ensure {
    ($what:expr, $error:expr) => {
        if !($what) {
            $crate::sysexit::system_exit_fatal($error, file!(), line!());
        }
    };
}

#[macro_export]
macro_rules! fatal_error {
    ($msg:expr) => {{
        $crate::sysexit::system_exit_fatal($msg, file!(), line!());
    }};
}

pub use ensure;
pub use fatal_error;
pub use unwrap;

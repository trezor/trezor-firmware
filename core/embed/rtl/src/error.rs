use crate::ffi;
use crate::util::FatPtr;

pub fn error_shutdown(message: &str, title: Option<&str>, footer: Option<&str>) -> ! {
    let message_ptr = FatPtr::from(message);
    let title_ptr = title.map(FatPtr::from).unwrap_or_else(FatPtr::null);
    let footer_ptr = footer.map(FatPtr::from).unwrap_or_else(FatPtr::null);

    // SAFETY: safe
    unsafe {
        ffi::error_shutdown_ex_n(
            message_ptr.ptr(),
            message_ptr.len(),
            title_ptr.ptr(),
            title_ptr.len(),
            footer_ptr.ptr(),
            footer_ptr.len(),
        );
    }
}

#[inline(never)] // saves few kilobytes of flash
pub fn __fatal_error(message: &str, file: &str, line: u32) -> ! {
    let message_ptr = FatPtr::from(message);
    let file_ptr = FatPtr::from(file);

    // SAFETY: safe
    unsafe {
        ffi::__fatal_error_n(
            message_ptr.ptr(),
            message_ptr.len(),
            file_ptr.ptr(),
            file_ptr.len(),
            line as i32,
        );
    }
}

pub trait UnwrapOrFatalError<T> {
    fn unwrap_or_fatal_error(self, msg: &str, file: &str, line: u32) -> T;
}

impl<T> UnwrapOrFatalError<T> for Option<T> {
    fn unwrap_or_fatal_error(self, msg: &str, file: &str, line: u32) -> T {
        match self {
            Some(x) => x,
            None => __fatal_error(msg, file, line),
        }
    }
}

impl<T, E> UnwrapOrFatalError<T> for Result<T, E> {
    fn unwrap_or_fatal_error(self, msg: &str, file: &str, line: u32) -> T {
        match self {
            Ok(x) => x,
            Err(_) => __fatal_error(msg, file, line),
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
            $crate::error::__fatal_error($error, file!(), line!());
        }
    };
}

#[macro_export]
macro_rules! fatal_error {
    ($msg:expr) => {{
        $crate::error::__fatal_error($msg, file!(), line!());
    }};
}

pub use ensure;
pub use fatal_error;
pub use unwrap;

use crate::ffi;
use crate::util::FatPtr;

pub fn system_exit_error(title: Option<&str>, message: &str, footer: Option<&str>) -> ! {
    let message_ptr = FatPtr::from(message);
    let title_ptr = title.map(FatPtr::from).unwrap_or_else(FatPtr::null);
    let footer_ptr = footer.map(FatPtr::from).unwrap_or_else(FatPtr::null);

    // SAFETY: safe
    unsafe {
        ffi::system_exit_error_ex(
            title_ptr.ptr(),
            title_ptr.len(),
            message_ptr.ptr(),
            message_ptr.len(),
            footer_ptr.ptr(),
            footer_ptr.len(),
        )
    }
}

#[inline(never)] // saves few kilobytes of flash
pub fn system_exit_fatal(message: &str, file: &str, line: u32) -> ! {
    let message_ptr = FatPtr::from(message);
    let file_ptr = FatPtr::from(file);

    // SAFETY: safe
    unsafe {
        ffi::system_exit_fatal_ex(
            message_ptr.ptr(),
            message_ptr.len(),
            file_ptr.ptr(),
            file_ptr.len(),
            line as i32,
        )
    }
}

pub trait UnwrapOrFatalError<T> {
    fn unwrap_or_fatal_error(self, msg: &str, file: &str, line: u32) -> T;
}

impl<T> UnwrapOrFatalError<T> for Option<T> {
    fn unwrap_or_fatal_error(self, msg: &str, file: &str, line: u32) -> T {
        match self {
            Some(x) => x,
            None => system_exit_fatal(msg, file, line),
        }
    }
}

impl<T, E> UnwrapOrFatalError<T> for Result<T, E> {
    fn unwrap_or_fatal_error(self, msg: &str, file: &str, line: u32) -> T {
        match self {
            Ok(x) => x,
            Err(_) => system_exit_fatal(msg, file, line),
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
            $crate::error::system_exit_fatal($error, file!(), line!());
        }
    };
}

#[macro_export]
macro_rules! fatal_error {
    ($msg:expr) => {{
        $crate::error::system_exit_fatal($msg, file!(), line!());
    }};
}

pub use ensure;
pub use fatal_error;
pub use unwrap;

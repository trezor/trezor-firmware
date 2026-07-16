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

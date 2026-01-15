pub trait UnwrapOrFatalError<T> {
    fn unwrap_or_fatal_error(self, msg: &str, file: &str, line: u32) -> T;
}

impl<T> UnwrapOrFatalError<T> for Option<T> {
    fn unwrap_or_fatal_error(self, msg: &str, file: &str, line: u32) -> T {
        match self {
            Some(x) => x,
            None => crate::low_level_api::system_exit_fatal(msg, file, line as i32),
        }
    }
}

impl<T, E> UnwrapOrFatalError<T> for Result<T, E> {
    fn unwrap_or_fatal_error(self, msg: &str, file: &str, line: u32) -> T {
        match self {
            Ok(x) => x,
            Err(_) => crate::low_level_api::system_exit_fatal(msg, file, line as i32),
        }
    }
}

#[macro_export]
macro_rules! unwrap {
    ($e:expr, $msg:expr) => {{
        use $crate::macros::UnwrapOrFatalError;
        $e.unwrap_or_fatal_error($msg, file!(), line!())
    }};
    ($expr:expr) => {
        unwrap!($expr, "unwrap failed")
    };
}

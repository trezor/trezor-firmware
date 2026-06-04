unsafe extern "Rust" {
    pub fn __fatal_error_rust(msg: &str, file: &str, line: u32) -> !;
}

pub(crate) fn __fatal_error(msg: &str, file: &str, line: u32) -> ! {
    #[cfg(test)]
    panic!("FATAL ERROR: {:?} at {}:{}", msg, file, line);
    #[cfg(not(test))]
    unsafe { __fatal_error_rust(msg, file, line) }
}

pub(crate) trait UnwrapOrFatalError<T> {
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


macro_rules! unwrap {
    ($e:expr, $msg:expr) => {{
        use $crate::error_util::UnwrapOrFatalError;
        $e.unwrap_or_fatal_error($msg, file!(), line!())
    }};
    ($expr:expr) => {
        unwrap!($expr, "unwrap failed")
    };
}

#[allow(unused_macros)]
macro_rules! ensure {
    ($what:expr, $error:expr) => {
        if !($what) {
            $crate::error_util::__fatal_error($error, file!(), line!());
        }
    };
}

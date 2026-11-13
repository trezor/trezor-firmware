pub trait UnwrapOrFatalError<T> {
    fn unwrap_or_fatal_error(self, msg: &str, file: &str, line: u32) -> T;
}

impl<T> UnwrapOrFatalError<T> for Option<T> {
    fn unwrap_or_fatal_error(self, msg: &str, file: &str, line: u32) -> T {
        match self {
            Some(x) => x,
            None => crate::app_runtime::system_exit_fatal(msg, file, line),
        }
    }
}

impl<T, E> UnwrapOrFatalError<T> for Result<T, E> {
    fn unwrap_or_fatal_error(self, msg: &str, file: &str, line: u32) -> T {
        match self {
            Ok(x) => x,
            Err(_) => crate::app_runtime::system_exit_fatal(msg, file, line),
        }
    }
}

/// Unwraps an [`Option`] or [`Result`], triggering a fatal error on failure.
///
/// On failure calls `system_exit_fatal`
/// with the file name, line number, and an optional custom message.
///
/// # Forms
///
/// **Without message** — failure prints `"unwrap failed"`:
/// ```
/// # use trezor_app_sdk::unwrap;
/// assert_eq!(unwrap!(Ok::<i32, &str>(42)), 42);
/// assert_eq!(unwrap!(Some(7)), 7);
/// ```
///
/// **With custom message** — failure prints the given message:
/// ```
/// # use trezor_app_sdk::unwrap;
/// assert_eq!(unwrap!(Ok::<i32, &str>(42), "must be Ok"), 42);
/// assert_eq!(unwrap!(Some(7), "must be Some"), 7);
/// ```
///
/// **Failing values** trigger a fatal error — do not run in tests:
/// ```no_run
/// # use trezor_app_sdk::unwrap;
/// unwrap!(Err::<i32, &str>("oops"));           // fatal — "unwrap failed"
/// unwrap!(Err::<i32, &str>("oops"), "message"); // fatal — custom message
/// unwrap!(None::<i32>);                         // fatal — "unwrap failed"
/// ```
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

//! Utility macros and traits for fatal-error unwrapping.
//!
//! This module provides the [`unwrap!`] macro and the [`UnwrapOrFatalError`] trait
//! for unwrapping `Option` and `Result` values in contexts where a failure is
//! considered a programming error that cannot be recovered from.
//!
//! # When to use
//!
//! Use [`unwrap!`] **only** when you are certain that the value cannot be `None`
//! or `Err` at runtime — i.e. when a failure would indicate a bug in the code.
//! If there is any realistic chance of failure, prefer propagating the error
//! with `?` or handling it explicitly instead.

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

/// Unwraps an [`Option`] or [`Result`], triggering a fatal error on failure.
///
/// # Forms
///
/// ```rust
/// unwrap!(expr)              // uses the default message "unwrap failed"
/// unwrap!(expr, "my message") // uses a custom message
/// ```
///
/// # When to use
///
/// Only use this macro when a `None` or `Err` would indicate a **bug** — i.e.
/// a situation that should never occur in correct code. If the failure is a
/// realistic runtime condition, return an error instead.
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

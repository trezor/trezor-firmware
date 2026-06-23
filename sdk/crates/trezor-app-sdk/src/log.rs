//! Logging module.
//!
//! Provides structured logging with compile-time level filtering.
//!
//! ## Usage
//!
//! ```rust
//! use trezor_app_sdk::{error, warn, info, debug, trace};
//!
//! info!("Application started");
//! debug!("Processing item: {}", item);
//! error!("Failed: {:?}", err);
//! ```
//!
//! ## Compile-time filtering
//!
//! Log level is controlled at build time via Cargo features. Enable exactly one of:
//!
//! ```toml
//! # Cargo.toml
//! [features]
//! log_level_error = []
//! log_level_warn  = []
//! log_level_info  = []
//! log_level_debug = []
//! log_level_trace = []
//! ```
//!
//! Each level implies all levels above it (e.g. `log_level_info` enables `error`,
//! `warn`, and `info`). If no feature is enabled, all log output is compiled out.
//!
//! The preferred way to set the log level is via `xtask`:
//!
//! ```bash
//! cargo xtask build --log-level info
//! ```
//!
//! Alternatively, pass the feature flag directly to Cargo:
//!
//! ```bash
//! cargo build --features log_level_info
//! ```

use crate::low_level_api;

/// Log level enumeration, ordered by severity (lowest value = highest severity).
#[doc(hidden)]
pub enum Level {
    Error = 1,
    Warn = 2,
    Info = 3,
    Debug = 4,
    Trace = 5,
}

impl Level {
    pub const fn as_str(&self) -> &'static str {
        match self {
            Level::Error => "ERROR",
            Level::Warn => "WARN ",
            Level::Info => "INFO ",
            Level::Debug => "DEBUG",
            Level::Trace => "TRACE",
        }
    }
}

/// Formats `timestamp` (milliseconds since boot) as a zero-padded 8-digit ASCII string
///
/// This function is `pub` only because it is called from the [`log!`] macro;
/// it is not part of the public API and should not be called directly.
#[doc(hidden)]
#[inline]
fn __format_timestamp(buf: &mut [u8], mut timestamp: u32) -> &str {
    buf.fill(b'0');
    let mut rcursor = buf.len() - 1;
    while timestamp > 0 {
        buf[rcursor] = (timestamp % 10) as u8 + b'0';
        timestamp /= 10;
        if rcursor == 0 {
            break;
        }
        rcursor -= 1;
    }
    // SAFETY: We just generated the data as ASCII digits.
    unsafe { core::str::from_utf8_unchecked(buf) }
}

/// Prints the log line header to the console in the format:
/// `[TTTTTTTT] LEVEL [module::path] `
///
/// Uses the system tick counter for the timestamp if the low-level API is initialized,
/// otherwise falls back to `0`.
///
/// This function is `pub` only because it is called from the [`log!`] macro;
/// it is not part of the public API and should not be called directly.
#[inline]
#[doc(hidden)]
pub fn __log_print_header(level: Level, module: &str) {
    let timestamp = if low_level_api::is_initialized() {
        low_level_api::systick_ms()
    } else {
        0
    };
    let mut timestamp_buf = [b'0'; 8];
    let timestamp_str = __format_timestamp(&mut timestamp_buf, timestamp);
    let _ = ufmt::uwrite!(
        crate::print::printer(),
        "[{}] {} [{}] ",
        timestamp_str,
        level.as_str(),
        module,
    );
}

// Private helper macro — exported only so the level-specific macros can call it
// from other crates. Do not use this macro directly.
#[doc(hidden)]
#[macro_export]
macro_rules! log {
    ($level:expr, $($args:tt)*) => {
        #[cfg(any(
            feature = "log_level_error",
            feature = "log_level_warn",
            feature = "log_level_info",
            feature = "log_level_debug",
            feature = "log_level_trace"
        ))]
        {
            $crate::log::__log_print_header($level, module_path!());
            let _ = ufmt::uwrite!($crate::print::printer(), $($args)*);
            $crate::print::print("\n");
        }
    }
}

/// Logs a message at the **ERROR** level.
///
/// Compiled in when any `log_level_*` feature is enabled, since `error` is the
/// highest-severity level and is always included when logging is active.
#[macro_export]
macro_rules! error {
    ($($arg:tt)*) => {
        #[cfg(any(
            feature = "log_level_error",
            feature = "log_level_warn",
            feature = "log_level_info",
            feature = "log_level_debug",
            feature = "log_level_trace"
        ))]
        {
            $crate::log::log!(
                $crate::log::Level::Error,
                $($arg)*
            );
        }
    };
}

/// Logs a message at the **WARN** level.
///
/// Compiled in when `log_level_warn` or a lower-severity feature is enabled.
#[macro_export]
macro_rules! warn_ {
    ($($arg:tt)*) => {
        #[cfg(any(
            feature = "log_level_warn",
            feature = "log_level_info",
            feature = "log_level_debug",
            feature = "log_level_trace"
        ))]
        {
            $crate::log::log!(
                $crate::log::Level::Warn,
                $($arg)*
            );
        }
    };
}

/// Logs a message at the **INFO** level.
///
/// Compiled in when `log_level_info`, `log_level_debug`, or `log_level_trace` is enabled.
#[macro_export]
macro_rules! info {
    ($($arg:tt)*) => {
        #[cfg(any(
            feature = "log_level_info",
            feature = "log_level_debug",
            feature = "log_level_trace"
        ))]
        {
            $crate::log::log!(
                $crate::log::Level::Info,
                $($arg)*
            );
        }
    };
}

/// Logs a message at the **DEBUG** level.
///
/// Compiled in when `log_level_debug` or `log_level_trace` is enabled.
#[macro_export]
macro_rules! debug {
    ($($arg:tt)*) => {
        #[cfg(any(
            feature = "log_level_debug",
            feature = "log_level_trace"
        ))]
        {
            $crate::log::log!(
                $crate::log::Level::Debug,
                $($arg)*
            );
        }
    };
}

/// Logs a message at the **TRACE** level.
///
/// Compiled in only when `log_level_trace` is enabled.
/// This is the most verbose level; use it for fine-grained diagnostic output.
#[macro_export]
macro_rules! trace {
    ($($arg:tt)*) => {
        #[cfg(any(
            feature = "log_level_trace"
        ))]
        {
            $crate::log::log!(
                $crate::log::Level::Trace,
                $($arg)*
            );
        }
    };
}

#[allow(unused_imports)]
pub use {debug, error, info, log, trace, warn_ as warn};

//! Logging module.
//!
//! Provides structured logging with compile-time level filtering.
//!
//! ## Usage
//!
//! ```rust
//! use trezor_app_sdk::{error, warn, info, debug};
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

/// Log level enumeration, ordered by severity.
#[doc(hidden)]
pub enum Level {
    Error,
    Warn,
    Info,
    Debug,
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
        ))]
        {
            $crate::print::start_print(module_path!(), $level);
            let _ = ufmt::uwrite!($crate::print::printer(), $($args)*);
            $crate::print::end_print();
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
/// Compiled in when `log_level_info` or `log_level_debug` is enabled.
#[macro_export]
macro_rules! info {
    ($($arg:tt)*) => {
        #[cfg(any(
            feature = "log_level_info",
            feature = "log_level_debug",
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
/// Compiled in when `log_level_debug` is enabled.
#[macro_export]
macro_rules! debug {
    ($($arg:tt)*) => {
        #[cfg(
            feature = "log_level_debug"
        )]
        {
            $crate::log::log!(
                $crate::log::Level::Debug,
                $($arg)*
            );
        }
    };
}

#[allow(unused_imports)]
pub use {debug, error, info, log, warn_ as warn};

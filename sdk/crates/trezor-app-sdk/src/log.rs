//! Logging module
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
//! Set log level at build time:
//! ```bash
//! RUSTFLAGS='--cfg log_level="info"' cargo build
//! ```

extern crate alloc;

/// Log level enumeration
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
#[repr(u8)]
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

/// Log record passed to the logger
pub struct Record<'a> {
    pub level: Level,
    pub module: &'a str,
    pub file: &'a str,
    pub line: u32,
    pub args: &'a str,
}

/// Logger trait - implement this for your custom backend
pub trait Logger {
    fn log(&self, record: &Record);
}

/// Helper function to format a log record with timestamp
#[inline]
pub fn format_with_timestamp(record: &Record, timestamp: u32) -> alloc::string::String {
    alloc::format!(
        "[{:08}] {} [{}] {}\n",
        timestamp,
        record.level.as_str(),
        record.module,
        record.args
    )
}

// Compile-time log level configuration
pub const MAX_LOG_LEVEL: Level = {
    #[cfg(log_level = "error")]
    {
        Level::Error
    }
    #[cfg(log_level = "warn")]
    {
        Level::Warn
    }
    #[cfg(log_level = "info")]
    {
        Level::Info
    }
    #[cfg(log_level = "debug")]
    {
        Level::Debug
    }
    #[cfg(log_level = "trace")]
    {
        Level::Trace
    }
    #[cfg(not(any(
        log_level = "off",
        log_level = "error",
        log_level = "warn",
        log_level = "info",
        log_level = "debug",
        log_level = "trace"
    )))]
    {
        Level::Info
    } // Default to Info
};

/// Internal logging function called by macros
#[doc(hidden)]
#[inline]
pub fn __log(level: Level, module: &str, file: &str, line: u32, args: &str) {
    #[cfg(not(log_level = "off"))]
    {
        let record = Record {
            level,
            module,
            file,
            line,
            args,
        };
        __logger().log(&record);
    }
}

/// Get the global logger instance
#[doc(hidden)]
pub fn __logger() -> &'static dyn Logger {
    extern "Rust" {
        fn __trezor_log_global_logger() -> &'static dyn Logger;
    }
    unsafe { __trezor_log_global_logger() }
}

/// Macro to define a global logger
///
/// ## Example
///
/// ```rust
/// use trezor_app_sdk::log::{Logger, Record, global_logger};
///
/// struct MyLogger;
///
/// impl Logger for MyLogger {
///     fn log(&self, record: &Record) {
///         // Your implementation
///     }
/// }
///
/// global_logger!(MyLogger);
/// ```
#[macro_export]
macro_rules! global_logger {
    ($logger_type:ty) => {
        #[no_mangle]
        fn __trezor_log_global_logger() -> &'static dyn $crate::log::Logger {
            static LOGGER: $logger_type = <$logger_type>::new();
            &LOGGER
        }
    };
}

// Re-export at module level
pub use global_logger;

/// Logging macros with compile-time level filtering
#[macro_export]
macro_rules! error {
    ($($arg:tt)*) => {{
        #[cfg(not(log_level = "off"))]
        if $crate::log::Level::Error <= $crate::log::MAX_LOG_LEVEL {
            let msg = alloc::format!($($arg)*);
            $crate::log::__log(
                $crate::log::Level::Error,
                module_path!(),
                file!(),
                line!(),
                &msg
            );
        }
    }};
}

#[macro_export]
macro_rules! warn {
    ($($arg:tt)*) => {{
        #[cfg(not(log_level = "off"))]
        if $crate::log::Level::Warn <= $crate::log::MAX_LOG_LEVEL {
            let msg = alloc::format!($($arg)*);
            $crate::log::__log(
                $crate::log::Level::Warn,
                module_path!(),
                file!(),
                line!(),
                &msg
            );
        }
    }};
}

#[macro_export]
macro_rules! info {
    ($($arg:tt)*) => {{
        #[cfg(not(log_level = "off"))]
        if $crate::log::Level::Info <= $crate::log::MAX_LOG_LEVEL {
            let msg = alloc::format!($($arg)*);
            $crate::log::__log(
                $crate::log::Level::Info,
                module_path!(),
                file!(),
                line!(),
                &msg
            );
        }
    }};
}

#[macro_export]
macro_rules! debug {
    ($($arg:tt)*) => {{
        #[cfg(not(log_level = "off"))]
        if $crate::log::Level::Debug <= $crate::log::MAX_LOG_LEVEL {
            let msg = alloc::format!($($arg)*);
            $crate::log::__log(
                $crate::log::Level::Debug,
                module_path!(),
                file!(),
                line!(),
                &msg
            );
        }
    }};
}

#[macro_export]
macro_rules! trace {
    ($($arg:tt)*) => {{
        #[cfg(not(log_level = "off"))]
        if $crate::log::Level::Trace <= $crate::log::MAX_LOG_LEVEL {
            let msg = alloc::format!($($arg)*);
            $crate::log::__log(
                $crate::log::Level::Trace,
                module_path!(),
                file!(),
                line!(),
                &msg
            );
        }
    }};
}

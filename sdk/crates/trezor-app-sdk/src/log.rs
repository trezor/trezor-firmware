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

/// Helper function to format a log record with timestamp
#[inline]
fn format_timestamp(buf: &mut [u8], mut timestamp: u32) -> &str {
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

#[inline]
pub fn __log_print_header(level: Level, module: &str) {
    let timestamp = if low_level_api::is_initialized() {
        low_level_api::systick_ms()
    } else {
        0
    };
    let mut timestamp_buf = [b'0'; 8];
    let timestamp_str = format_timestamp(&mut timestamp_buf, timestamp);
    let _ = ufmt::uwrite!(
        crate::print::printer(),
        "[{}] {} [{}] ",
        timestamp_str,
        level.as_str(),
        module,
    );
}

/// Internal logging function called by macros
#[macro_export]
macro_rules! log {
    ($level:expr, $($args:tt)*) => {
        #[cfg(not(log_level = "off"))]
        {
            $crate::log::__log_print_header($level, module_path!());
            let _ = ufmt::uwrite!($crate::print::printer(), $($args)*);
            $crate::print::print("\n");
        }
    }
}

/// Logging macros with compile-time level filtering
#[macro_export]
macro_rules! error {
    ($($arg:tt)*) => {
        #[cfg(any(
            log_level = "error",
            log_level = "warn",
            log_level = "info",
            log_level = "debug",
            log_level = "trace"
        ))]
        {
            $crate::log::log!(
                $crate::log::Level::Error,
                $($arg)*
            );
        }
    };
}

#[macro_export]
macro_rules! warn_internal {
    ($($arg:tt)*) => {
        #[cfg(any(
            log_level = "warn",
            log_level = "info",
            log_level = "debug",
            log_level = "trace"
        ))]
        {
            $crate::log::log!(
                $crate::log::Level::Warn,
                $($arg)*
            );
        }
    };
}

#[macro_export]
macro_rules! warn {
    ($($arg:tt)*) => {
        $crate::log::warn_internal!($($arg)*);
    };
}

#[macro_export]
macro_rules! info {
    ($($arg:tt)*) => {
        #[cfg(any(
            log_level = "info",
            log_level = "debug",
            log_level = "trace"
        ))]
        {
            $crate::log::log!(
                $crate::log::Level::Info,
                $($arg)*
            );
        }
    };
}

#[macro_export]
macro_rules! debug {
    ($($arg:tt)*) => {
        #[cfg(any(
            log_level = "debug",
            log_level = "trace"
        ))]
        {
            $crate::log::log!(
                $crate::log::Level::Debug,
                $($arg)*
            );
        }
    };
}

#[macro_export]
macro_rules! trace {
    ($($arg:tt)*) => {
        #[cfg(any(
            log_level = "trace"
        ))]
        {
            $crate::log::log!(
                $crate::log::Level::Trace,
                $($arg)*
            );
        }
    };
}

use {crate::low_level_api};
#[allow(unused_imports)]
pub use {log, error, warn_internal, warn_internal as warn, info, debug, trace};

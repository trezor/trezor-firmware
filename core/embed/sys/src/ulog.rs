//! ufmt-based logging macros.
//!
//! Similar to the `log` crate but with only basic features and using ufmt
//! instead of core::fmt. When logging is disabled, the invocation is dead code
//! and gets optimized out.

use super::ffi;

#[derive(Debug, PartialEq, Eq, PartialOrd, Clone, Copy)]
pub enum LogLevel {
    /// Not a real level, used for filtering
    Off = ffi::log_level_t_LOG_LEVEL_OFF as _,
    Error = ffi::log_level_t_LOG_LEVEL_ERR as _,
    Warn = ffi::log_level_t_LOG_LEVEL_WARN as _,
    Info = ffi::log_level_t_LOG_LEVEL_INF as _,
    Debug = ffi::log_level_t_LOG_LEVEL_DBG as _,
}

#[doc(hidden)]
pub mod __private {
    // `uwrite!` expands to relative `ufmt::` paths. Importing it in the macro
    // body saves callers from having to depend on `ufmt` directly.
    pub use ufmt;

    #[cfg(feature = "dbg_console")]
    pub use crate::syslog::log;

    /// Dummy `syslog::log` to use without `dbg_console`.
    #[cfg(not(feature = "dbg_console"))]
    pub fn log<T, E, F>(_module: &str, _level: super::LogLevel, _log_fn: F) -> Result<Option<T>, E>
    where
        F: FnOnce(&mut dyn ufmt::uWrite<Error = ()>) -> Result<T, E>,
    {
        unreachable!()
    }
}

// Static maximum log level used to optimize out calls with higher level at
// compile-time.
pub const STATIC_MAX_LEVEL: LogLevel = if !cfg!(feature = "dbg_console") {
    LogLevel::Off
} else if cfg!(feature = "log_max_debug") {
    LogLevel::Debug
} else if cfg!(feature = "log_max_info") {
    LogLevel::Info
} else if cfg!(feature = "log_max_warn") {
    LogLevel::Warn
} else if cfg!(feature = "log_max_error") {
    LogLevel::Error
} else {
    LogLevel::Off
};

// `#[macro_export]` places macros at the crate root, so they are exported under
// hidden unique names and only get their public names in this module.
#[doc(hidden)]
#[macro_export]
macro_rules! __ulog_log {
    ($level:expr, $($args:tt)+) => ({
        if $level <= $crate::ulog::STATIC_MAX_LEVEL {
            use $crate::ulog::__private::ufmt;
            $crate::ulog::__private::log(core::module_path!(), $level, |writer| {
                ufmt::uwrite!(writer, $($args)+)
            }).ok();
        }
    })
}

#[doc(hidden)]
#[macro_export]
macro_rules! __ulog_debug {
    ($($args:tt)+) => ({
        $crate::ulog::log!($crate::ulog::LogLevel::Debug, $($args)+)
    })
}

#[doc(hidden)]
#[macro_export]
macro_rules! __ulog_info {
    ($($args:tt)+) => ({
        $crate::ulog::log!($crate::ulog::LogLevel::Info, $($args)+)
    })
}

#[doc(hidden)]
#[macro_export]
macro_rules! __ulog_warn {
    ($($args:tt)+) => ({
        $crate::ulog::log!($crate::ulog::LogLevel::Warn, $($args)+)
    })
}

#[doc(hidden)]
#[macro_export]
macro_rules! __ulog_error {
    ($($args:tt)+) => ({
        $crate::ulog::log!($crate::ulog::LogLevel::Error, $($args)+)
    })
}

pub use __ulog_debug as debug;
pub use __ulog_error as error;
pub use __ulog_info as info;
pub use __ulog_log as log;
pub use __ulog_warn as warn;

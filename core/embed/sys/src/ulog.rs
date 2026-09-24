#[macro_export]
macro_rules! log {
    ($level:expr, $($args:tt)+) => ({
        #[cfg(feature = "debug")]
        $crate::syslog::log(core::module_path!(), $level, |writer| {
            ufmt::uwrite!(writer, $($args)+)
        }).ok();
    })
}

#[macro_export]
macro_rules! debug {
    ($($args:tt)+) => ({
        $crate::ulog::log!($crate::syslog::LogLevel::Debug, $($args)+)
    })
}

#[macro_export]
macro_rules! info {
    ($($args:tt)+) => ({
        $crate::ulog::log!($crate::syslog::LogLevel::Info, $($args)+)
    })
}

// `warn` conflicts with a builtin attribute
#[macro_export]
macro_rules! warning {
    ($($args:tt)+) => ({
        $crate::ulog::log!($crate::syslog::LogLevel::Warn, $($args)+)
    })
}

#[macro_export]
macro_rules! error {
    ($($args:tt)+) => ({
        $crate::ulog::log!($crate::syslog::LogLevel::Error, $($args)+)
    })
}

pub use debug;
pub use error;
pub use info;
pub use log;
pub use warning;

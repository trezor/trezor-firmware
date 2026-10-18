//! Stand-in for [`syslog`](crate::syslog) without the `dbg_console` feature.
//!
//! The C syslog is not built then, so every record is dropped, just like the C
//! `LOG_*` macros. Only the items used outside a `dbg_console` build are here.

pub use crate::ulog::LogLevel;

/// Never constructed: [`log`] drops every record without calling `log_fn`.
pub struct SyslogChunkWriter(());

impl SyslogChunkWriter {
    pub fn write(&self, _s: &str) -> Result<(), ()> {
        Err(())
    }
}

pub fn log<T, E, F>(_module: &str, _level: LogLevel, _log_fn: F) -> Result<Option<T>, E>
where
    F: FnOnce(&mut SyslogChunkWriter) -> Result<T, E>,
{
    Ok(None)
}

pub fn log_simple(_module: &str, _level: LogLevel, _message: &str) {}

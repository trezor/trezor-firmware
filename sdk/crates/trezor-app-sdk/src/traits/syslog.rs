use stabby::str::Str;

use super::util::FastResult;

/// Severity of a log message.
#[stabby::stabby]
#[repr(u8)]
pub enum LogLevel {
    /// An error.
    Error = 1,
    /// A warning.
    Warn = 2,
    /// Information.
    Info = 3,
    /// Debugging output.
    Debug = 4,
}

#[stabby::stabby(checked)]
/// A log line being written, piece by piece.
pub trait LogRecord {
    /// Appends `string` to the log line.
    extern "C" fn write<'a>(&self, string: Str<'a>) -> FastResult<(), ()>;
}

#[stabby::stabby(checked)]
/// Writes a log message into the [`LogRecord`] it is given.
pub trait LogCallback {
    /// Writes the message into `record`.
    extern "C" fn call<'a>(&self, record: LogRecordRef<'a>) -> FastResult<(), ()>;
}

/// A borrowed `dyn LogRecord`.
pub type LogRecordRef<'a> = stabby::dynptr!(&'a dyn LogRecord);
/// A borrowed `dyn LogCallback`.
pub type LogCallbackRef<'a> = stabby::dynptr!(&'a dyn LogCallback);

#[stabby::stabby(checked)]
/// Logging to Core's system log.
pub trait SyslogV1: Send + Sync {
    /// Logs `message` at `level`.
    extern "C" fn log_simple<'a>(&self, level: LogLevel, message: Str<'a>);

    /// Logs at `level` a message that `callback` writes; skipped without calling
    /// `callback` if the level is filtered out.
    extern "C" fn log<'a>(&self, level: LogLevel, callback: LogCallbackRef<'a>);
}

/// The stabby vtable of [`SyslogV1`].
pub type SyslogV1Vtable = stabby::vtable!(SyslogV1 + Send + Sync);
/// A borrowed `dyn SyslogV1`.
pub type SyslogV1Ref<'a> = stabby::DynRef<'a, SyslogV1Vtable>;
/// A `dyn SyslogV1` that lives as long as the app.
pub type StaticSyslogV1 = SyslogV1Ref<'static>;

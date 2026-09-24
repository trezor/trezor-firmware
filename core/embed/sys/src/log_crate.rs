//! Connects the `log::error!`, `log::warn!`, ... macros from the `log` crate to
//! our C logging backend.

use core::fmt::Write as _;
use core::sync::atomic::{AtomicBool, Ordering};

use log::{Level, LevelFilter, Log, Metadata, Record, set_logger, set_max_level};

use crate::syslog;

static INITIALIZED: AtomicBool = AtomicBool::new(false);

struct SysLogger;

fn sys_level(level: Level) -> syslog::LogLevel {
    match level {
        Level::Error => syslog::LogLevel::Error,
        Level::Warn => syslog::LogLevel::Warn,
        Level::Info => syslog::LogLevel::Info,
        Level::Debug | Level::Trace => syslog::LogLevel::Debug,
    }
}

impl Log for SysLogger {
    fn enabled(&self, _metadata: &Metadata) -> bool {
        // The `log` crate already compares the level, `syslog_start_record` takes care
        // of filtering by module. Implementing it here would only make sense if we used
        // `log_enabled!` heavily.
        true
    }

    fn log(&self, record: &Record) {
        if !self.enabled(record.metadata()) {
            return;
        }

        syslog::log(record.target(), sys_level(record.level()), |write| {
            write.write_fmt(*record.args())
        })
        .ok();
    }

    fn flush(&self) {}
}

pub fn init() {
    #[cfg(not(feature = "log_crate_disabled"))]
    if !INITIALIZED.swap(true, Ordering::Relaxed) {
        let _ = set_logger(&SysLogger);
        set_max_level(LevelFilter::Trace);
    }
}

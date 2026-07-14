//! Connects the `log::error!`, `log::warn!`, ... macros from the `log` crate to
//! our C logging backend.

use log::{set_logger, set_max_level, Level, LevelFilter, Log, Metadata, Record};
use sys::syslog;

use core::{
    fmt::Write as _,
    sync::atomic::{AtomicBool, Ordering},
};

#[cfg(test)]
const MAX_MESSAGE_LEN: usize = 512;
#[cfg(not(test))]
const MAX_MESSAGE_LEN: usize = 128;

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

fn to_filter(val: u8) -> LevelFilter {
    match val {
        0 => LevelFilter::Trace, // corresponds to debug in micropython
        1 => LevelFilter::Info,
        2 => LevelFilter::Warn,
        3 => LevelFilter::Error,
        _ => LevelFilter::Off,
    }
}

pub fn init_rust_logging(level: u8) {
    if !INITIALIZED.swap(true, Ordering::Relaxed) {
        let _ = set_logger(&SysLogger);
        set_max_level(to_filter(level));
    }
}

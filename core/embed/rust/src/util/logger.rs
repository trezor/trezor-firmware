//! Connects the `log::error!`, `log::warn!`, ... macros from the `log` crate to
//! our C logging backend.

use heapless::Vec;
use log::{set_logger, set_max_level, Level, LevelFilter, Log, Metadata, Record};

use core::{
    fmt::Write,
    sync::atomic::{AtomicBool, Ordering},
};

use crate::trezorhal::syslog::{syslog_start_record, syslog_write_chunk, LogLevel};

const MAX_MESSAGE_LEN: usize = 128;

static INITIALIZED: AtomicBool = AtomicBool::new(false);

struct SysLogger;

fn sys_level(level: Level) -> LogLevel {
    match level {
        Level::Error => LogLevel::Error,
        Level::Warn => LogLevel::Warn,
        Level::Info => LogLevel::Info,
        Level::Debug | Level::Trace => LogLevel::Debug,
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

        let should_log = syslog_start_record(record.target(), sys_level(record.level()));
        if !should_log {
            return;
        }

        let mut msg = Vec::<u8, MAX_MESSAGE_LEN>::new();
        // Might still get partial message on error.
        let _ = msg.write_fmt(*record.args());

        // SAFETY: passed to C which doesn't care about UTF-8
        let text = unsafe { str::from_utf8_unchecked(&msg) };
        syslog_write_chunk(text, true);
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

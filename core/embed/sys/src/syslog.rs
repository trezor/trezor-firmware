//! App and Rust logging into the C syslog.
//!
//! Always available. Without the `dbg_console` feature the C syslog is not
//! built, and every record is dropped, just like the C `LOG_*` macros.

#[cfg(feature = "dbg_console")]
use rtl::CSlice;

#[cfg(feature = "dbg_console")]
use super::ffi;

/// Log level, numbered as the C `log_level_t`.
#[derive(PartialEq, Debug, Eq, Clone, Copy)]
#[repr(u8)]
pub enum LogLevel {
    Error = 1,
    Warn = 2,
    Info = 3,
    Debug = 4,
}

#[cfg(feature = "dbg_console")]
const _: () = {
    assert!(LogLevel::Error as ffi::log_level_t == ffi::log_level_t_LOG_LEVEL_ERR);
    assert!(LogLevel::Warn as ffi::log_level_t == ffi::log_level_t_LOG_LEVEL_WARN);
    assert!(LogLevel::Info as ffi::log_level_t == ffi::log_level_t_LOG_LEVEL_INF);
    assert!(LogLevel::Debug as ffi::log_level_t == ffi::log_level_t_LOG_LEVEL_DBG);
};

#[cfg(feature = "dbg_console")]
impl From<&str> for ffi::log_source_t {
    fn from(s: &str) -> Self {
        let ptr = CSlice::from(s);
        ffi::log_source_t {
            name: ptr.ptr(),
            name_len: ptr.len(),
        }
    }
}

#[cfg(feature = "dbg_console")]
fn syslog_start_record(module: &str, level: LogLevel) -> bool {
    let syslog_info = module.into();
    unsafe { ffi::syslog_start_record(&syslog_info, level as ffi::log_level_t) }
}

#[cfg(not(feature = "dbg_console"))]
fn syslog_start_record(_module: &str, _level: LogLevel) -> bool {
    false
}

#[cfg(feature = "dbg_console")]
fn syslog_write_chunk(text: &str, end_record: bool) -> Result<usize, ()> {
    let text = CSlice::from(text);
    let bytes_written = unsafe { ffi::syslog_write_chunk(text.ptr(), text.len(), end_record) };
    if bytes_written < 0 {
        Err(())
    } else {
        Ok(bytes_written as usize)
    }
}

#[cfg(not(feature = "dbg_console"))]
fn syslog_write_chunk(_text: &str, _end_record: bool) -> Result<usize, ()> {
    Err(())
}

/// Object for writing to the syslog chunk.
///
/// Has a private field to prevent construction outside of this module.
/// Assumes that whoever owns the instance has properly started a new record
/// via [`syslog_start_record`], and will properly end the record via
/// [`syslog_write_chunk`] with `end_record` set to `true`.
///
/// Implements `core::fmt::Write` for callers that need it.
pub struct SyslogChunkWriter(());

impl SyslogChunkWriter {
    pub fn write(&self, s: &str) -> Result<(), ()> {
        syslog_write_chunk(s, false)?;
        // TODO: check write length?
        Ok(())
    }
}

impl core::fmt::Write for SyslogChunkWriter {
    fn write_str(&mut self, s: &str) -> core::fmt::Result {
        self.write(s).map_err(|_| core::fmt::Error)
    }
}

impl ufmt::uWrite for SyslogChunkWriter {
    type Error = ();

    fn write_str(&mut self, s: &str) -> Result<(), Self::Error> {
        self.write(s)
    }
}

pub fn log<T, E, F>(module: &str, level: LogLevel, log_fn: F) -> Result<Option<T>, E>
where
    F: FnOnce(&mut SyslogChunkWriter) -> Result<T, E>,
{
    if syslog_start_record(module, level) {
        let mut writer = SyslogChunkWriter(());

        match log_fn(&mut writer) {
            Ok(result) => {
                syslog_write_chunk("", true).ok();
                Ok(Some(result))
            }
            Err(e) => {
                syslog_write_chunk("#INTERRUPTED", true).ok();
                Err(e)
            }
        }
    } else {
        Ok(None)
    }
}

pub fn log_simple(module: &str, level: LogLevel, message: &str) {
    if syslog_start_record(module, level) {
        syslog_write_chunk(message, true).ok();
    }
}

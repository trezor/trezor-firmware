use super::ffi;

#[derive(PartialEq, Debug, Eq, Clone, Copy)]
pub enum LogLevel {
    Debug = ffi::log_level_t_LOG_LEVEL_DBG as _,
    Info = ffi::log_level_t_LOG_LEVEL_INF as _,
    Warn = ffi::log_level_t_LOG_LEVEL_WARN as _,
    Error = ffi::log_level_t_LOG_LEVEL_ERR as _,
}

impl ffi::log_source_t {
    fn new(module: &str) -> Self {
        Self {
            name: module.as_ptr() as *const cty::c_char,
            name_len: module.len(),
        }
    }
}

fn syslog_start_record(module: &str, level: LogLevel) -> bool {
    let syslog_info = ffi::log_source_t::new(module);
    unsafe {
        ffi::syslog_start_record(
            &syslog_info as *const ffi::log_source_t,
            level as ffi::log_level_t,
        )
    }
}

fn syslog_write_chunk(text: &str, end_record: bool) -> isize {
    unsafe { ffi::syslog_write_chunk(text.as_ptr() as *const cty::c_char, text.len(), end_record) }
}

/// Object for writing to the syslog chunk.
///
/// Has a private field to prevent construction outside of this module.
/// Assumes that whoever owns the instance has properly started a new record
/// via [`syslog_start_record`], and will properly end the record via [`syslog_write_chunk`]
/// with `end_record` set to `true`.
///
/// Implements `core::fmt::Write` for callers that need it.
pub struct SyslogChunkWriter(());

impl SyslogChunkWriter {
    pub fn write(&self, s: &str) {
        syslog_write_chunk(s, false);
    }
}

impl core::fmt::Write for SyslogChunkWriter {
    fn write_str(&mut self, s: &str) -> core::fmt::Result {
        self.write(s);
        Ok(())
    }
}

impl ufmt::uWrite for SyslogChunkWriter {
    type Error = core::convert::Infallible;

    fn write_str(&mut self, s: &str) -> Result<(), Self::Error> {
        self.write(s);
        Ok(())
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
                syslog_write_chunk("", true);
                Ok(Some(result))
            }
            Err(e) => {
                syslog_write_chunk("#INTERRUPTED", true);
                Err(e)
            }
        }
    } else {
        Ok(None)
    }
}

use super::ffi;

#[derive(PartialEq, Debug, Eq, FromPrimitive, Clone, Copy)]
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

pub fn syslog_start_record(module: &str, level: LogLevel) -> bool {
    let syslog_info = ffi::log_source_t::new(module);
    unsafe {
        ffi::syslog_start_record(
            &syslog_info as *const ffi::log_source_t,
            level as ffi::log_level_t,
        )
    }
}

pub fn syslog_write_chunk(text: &str, end_record: bool) -> isize {
    unsafe { ffi::syslog_write_chunk(text.as_ptr() as *const cty::c_char, text.len(), end_record) }
}

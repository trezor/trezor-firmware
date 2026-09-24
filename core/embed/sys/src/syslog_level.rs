use super::ffi;

#[derive(PartialEq, Debug, Eq, Clone, Copy)]
pub enum LogLevel {
    Debug = ffi::log_level_t_LOG_LEVEL_DBG as _,
    Info = ffi::log_level_t_LOG_LEVEL_INF as _,
    Warn = ffi::log_level_t_LOG_LEVEL_WARN as _,
    Error = ffi::log_level_t_LOG_LEVEL_ERR as _,
}

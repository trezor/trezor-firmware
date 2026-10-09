use super::ffi;

#[derive(Debug, PartialEq, Eq, PartialOrd, Clone, Copy)]
pub enum LogLevel {
    /// Not a real level, used for filtering
    Off = ffi::log_level_t_LOG_LEVEL_OFF as _,
    Error = ffi::log_level_t_LOG_LEVEL_ERR as _,
    Warn = ffi::log_level_t_LOG_LEVEL_WARN as _,
    Info = ffi::log_level_t_LOG_LEVEL_INF as _,
    Debug = ffi::log_level_t_LOG_LEVEL_DBG as _,
}

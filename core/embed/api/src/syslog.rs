use stabby::str::Str;
use sys::syslog;
use trezor_app_sdk::traits::syslog::{
    LogCallbackDyn as _, LogCallbackRef, LogLevel as SdkLogLevel, LogRecord, LogRecordRef, SyslogV1,
};
use trezor_app_sdk::traits::util::FastResult;

pub struct TrezorSyslogV1Impl;

fn to_log_level(level: SdkLogLevel) -> syslog::LogLevel {
    match level {
        SdkLogLevel::Debug => syslog::LogLevel::Debug,
        SdkLogLevel::Info => syslog::LogLevel::Info,
        SdkLogLevel::Warn => syslog::LogLevel::Warn,
        SdkLogLevel::Error => syslog::LogLevel::Error,
    }
}

struct LogRecordProxy<'a>(&'a mut syslog::SyslogChunkWriter);

impl LogRecord for LogRecordProxy<'_> {
    extern "C" fn write<'a>(&self, string: Str<'a>) -> FastResult<(), ()> {
        self.0.write(string.as_str());
        Ok(()).into()
    }
}

fn get_app_name() -> &'static str {
    "extapp" // TODO: get app name from metadata
}

impl SyslogV1 for TrezorSyslogV1Impl {
    extern "C" fn log_simple<'a>(&self, level: SdkLogLevel, message: Str<'a>) {
        sys::syslog::log_simple(get_app_name(), to_log_level(level), message.as_str());
    }

    extern "C" fn log<'a>(&self, level: SdkLogLevel, callback: LogCallbackRef<'a>) {
        let _ = sys::syslog::log(get_app_name(), to_log_level(level), |writer| {
            let proxy = LogRecordProxy(writer);
            callback.call(LogRecordRef::from(&proxy)).into_result()
        });
    }
}

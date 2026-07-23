use stabby::str::Str;

use super::util::FastResult;

#[stabby::stabby]
#[repr(u8)]
pub enum LogLevel {
    Error = 1,
    Warn = 2,
    Info = 3,
    Debug = 4,
}

#[stabby::stabby(checked)]
pub trait LogRecord {
    extern "C" fn write<'a>(&self, string: Str<'a>) -> FastResult<(), ()>;
}

#[stabby::stabby(checked)]
pub trait LogCallback {
    extern "C" fn call<'a>(&self, record: LogRecordRef<'a>) -> FastResult<(), ()>;
}

pub type LogRecordRef<'a> = stabby::dynptr!(&'a dyn LogRecord);
pub type LogCallbackRef<'a> = stabby::dynptr!(&'a dyn LogCallback);

#[stabby::stabby(checked)]
pub trait SyslogV1: Send + Sync {
    extern "C" fn log_simple<'a>(&self, level: LogLevel, message: Str<'a>);
    extern "C" fn log<'a>(&self, level: LogLevel, callback: LogCallbackRef<'a>);
}

pub type SyslogV1Vtable = stabby::vtable!(SyslogV1 + Send + Sync);
pub type SyslogV1Ref<'a> = stabby::DynRef<'a, SyslogV1Vtable>;

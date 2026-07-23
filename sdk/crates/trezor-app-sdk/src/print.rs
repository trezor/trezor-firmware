use core::cell::RefCell;

use stabby::str::Str;

use crate::app_runtime2;
use crate::traits::syslog::{
    LogCallback, LogCallbackRef, LogLevel, LogRecordDyn, LogRecordRef, StaticSyslogV1, SyslogV1,
    SyslogV1Dyn as _,
};
use crate::traits::util::FastResult;

#[cfg(not(target_os = "none"))]
mod unix_ffi {
    use stabby::str::Str;

    use crate::traits::syslog::{
        LogCallbackDyn as _, LogCallbackRef, LogLevel, LogRecord, SyslogV1,
    };
    use crate::traits::util::FastResult;

    const STDOUT_FILENO: cty::c_int = 1;

    unsafe extern "C" {
        pub unsafe fn write(fd: cty::c_int, buf: *const u8, count: cty::size_t) -> cty::ssize_t;
    }

    pub fn print(to_log: &str) {
        // SAFETY: We're passing valid pointers and sizes.
        unsafe {
            write(STDOUT_FILENO, to_log.as_ptr(), to_log.len() as cty::size_t);
        }
    }

    pub struct UnixLogger;

    impl SyslogV1 for UnixLogger {
        extern "C" fn log_simple<'a>(&self, _level: LogLevel, message: Str<'a>) {
            print(message.as_str());
        }
        extern "C" fn log<'a>(&self, _level: LogLevel, callback: LogCallbackRef<'a>) {
            callback.call(self.into());
        }
    }

    impl LogRecord for UnixLogger {
        extern "C" fn write<'a>(&self, string: Str<'a>) -> FastResult<(), ()> {
            print(string.as_str());
            Ok(()).into()
        }
    }
}

pub struct NoOutput;

impl SyslogV1 for NoOutput {
    extern "C" fn log_simple<'a>(&self, _level: LogLevel, _message: Str<'a>) {}
    extern "C" fn log<'a>(&self, _level: LogLevel, _callback: LogCallbackRef<'a>) {}
}

pub struct LocalWriter<'a>(LogRecordRef<'a>);

impl LocalWriter<'_> {
    fn write(&self, s: &str) -> Result<(), ()> {
        self.0.write(s.into()).into_result()
    }
}

impl<'a> ufmt::uWrite for LocalWriter<'a> {
    type Error = ();

    fn write_str(&mut self, s: &str) -> Result<(), Self::Error> {
        Self::write(self, s)
    }
}

fn syslog() -> StaticSyslogV1 {
    if let Some(syslog) = app_runtime2::try_get_syslog() {
        return syslog;
    }
    if cfg!(not(target_os = "none")) {
        (&unix_ffi::UnixLogger).into()
    } else {
        (&NoOutput).into()
    }
}

pub fn log_simple(level: LogLevel, message: &str) {
    syslog().log_simple(level, message.into());
}

struct FnOnceWrapper<F> {
    callback: RefCell<Option<F>>,
}

impl<F> FnOnceWrapper<F> {
    fn new(callback: F) -> Self {
        Self {
            callback: RefCell::new(Some(callback)),
        }
    }
}

impl<F> LogCallback for FnOnceWrapper<F>
where
    F: for<'a> FnOnce(LocalWriter<'a>) -> Result<(), ()>,
{
    extern "C" fn call<'a>(&self, record: LogRecordRef<'a>) -> FastResult<(), ()> {
        self.callback
            .borrow_mut()
            .take()
            .map(|callback| callback(LocalWriter(record)))
            .unwrap_or(Err(()))
            .into()
    }
}

pub fn log(level: LogLevel, callback: impl FnOnce(LocalWriter) -> Result<(), ()>) {
    let callback = FnOnceWrapper::new(callback);
    syslog().log(level, (&callback).into());
}

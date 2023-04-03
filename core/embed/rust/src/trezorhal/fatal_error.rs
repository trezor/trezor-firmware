mod ffi {
    extern "C" {
        // trezorhal/common.c
        pub fn trezor_shutdown() -> !;
    }
}

use crate::ui::screens::screen_fatal_error;

fn shutdown() -> ! {
    unsafe { ffi::trezor_shutdown() }
}

#[cfg(feature = "bootloader")]
pub fn __fatal_error(_expr: &str, _msg: &str, _file: &str, _line: u32, _func: &str) -> ! {
    screen_fatal_error("BL.rs", "BL.rs", "PLEASE VISIT\nTREZOR.IO/RSOD");
    shutdown()
}

#[cfg(not(feature = "bootloader"))]
pub fn __fatal_error(_expr: &str, msg: &str, _file: &str, _line: u32, _func: &str) -> ! {
    screen_fatal_error("INTERNAL_ERROR", msg, "PLEASE VISIT\nTREZOR.IO/RSOD");
    shutdown()
}

pub trait UnwrapOrFatalError<T> {
    fn unwrap_or_fatal_error(self, expr: &str, msg: &str, file: &str, line: u32, func: &str) -> T;
}

impl<T> UnwrapOrFatalError<T> for Option<T> {
    fn unwrap_or_fatal_error(self, expr: &str, msg: &str, file: &str, line: u32, func: &str) -> T {
        match self {
            Some(x) => x,
            None => __fatal_error(expr, msg, file, line, func),
        }
    }
}

impl<T, E> UnwrapOrFatalError<T> for Result<T, E> {
    fn unwrap_or_fatal_error(self, expr: &str, msg: &str, file: &str, line: u32, func: &str) -> T {
        match self {
            Ok(x) => x,
            Err(_) => __fatal_error(expr, msg, file, line, func),
        }
    }
}

macro_rules! function_name {
    () => {{
        #[cfg(not(feature = "bootloader"))]
        {
            fn f() {}
            fn type_name_of<T>(_: T) -> &'static str {
                core::any::type_name::<T>()
            }
            let name = type_name_of(f);
            name.get(..name.len() - 3).unwrap_or("")
        }
        #[cfg(feature = "bootloader")]
        {
            ""
        }
    }};
}

macro_rules! unwrap {
    ($e:expr, $msg:expr) => {{
        use crate::trezorhal::fatal_error::UnwrapOrFatalError;
        $e.unwrap_or_fatal_error(stringify!($e), $msg, file!(), line!(), function_name!())
    }};
    ($expr:expr) => {
        unwrap!($expr, "unwrap failed")
    };
}

macro_rules! ensure {
    ($what:expr, $error:expr) => {
        if !($what) {
            fatal_error!(stringify!($what), $error);
        }
    };
}

macro_rules! fatal_error {
    ($expr:expr, $msg:expr) => {{
        crate::trezorhal::fatal_error::__fatal_error(
            stringify!($expr),
            $msg,
            file!(),
            line!(),
            function_name!(),
        );
    }};
}

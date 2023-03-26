mod ffi {
    extern "C" {
        // trezorhal/common.c
        pub fn shutdown() -> !;
    }
}

use crate::ui::screens::screen_fatal_error;
#[cfg(not(feature = "bootloader"))]
use heapless::String;

#[cfg(not(feature = "bootloader"))]
use crate::ui::util::u32_to_str;

fn shutdown() -> ! {
    unsafe { ffi::shutdown() }
}

#[cfg(feature = "bootloader")]
pub fn __fatal_error(_expr: &str, _msg: &str, _file: &str, _line: u32, _func: &str) -> ! {
    screen_fatal_error(Some("BL.rs"), "BL.rs");
    shutdown()
}

#[cfg(not(feature = "bootloader"))]
pub fn __fatal_error(_expr: &str, msg: &str, file: &str, line: u32, _func: &str) -> ! {
    let mut buf: String<256> = String::new();
    let _ = buf.push_str(file); // Nothing we can do if this fails
    let _ = buf.push_str(": ");

    let mut line_buf = [0u8; 10];
    if let Some(text) = u32_to_str(line, &mut line_buf) {
        let _ = buf.push_str(text);
    }

    screen_fatal_error(Some(msg), buf.as_str());
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

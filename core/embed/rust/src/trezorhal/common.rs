mod ffi {
    extern "C" {
        // trezorhal/common.c
        pub fn __fatal_error(
            expr: *const cty::c_char,
            msg: *const cty::c_char,
            file: *const cty::c_char,
            line: i32,
            func: *const cty::c_char,
        ) -> !;
    }
}

pub fn __fatal_error(expr: &str, msg: &str, file: &str, line: u32, func: &str) -> ! {
    const MAX_LEN: usize = 50 + 1; // Leave space for the null terminator.

    fn as_cstr_buf(s: &str) -> [cty::c_char; MAX_LEN] {
        let mut buf = [0 as cty::c_char; MAX_LEN];
        for (i, c) in s.as_bytes().iter().enumerate() {
            if i >= MAX_LEN {
                break;
            }
            buf[i] = *c as cty::c_char;
        }
        buf[MAX_LEN - 1] = 0;
        buf
    }

    let expr_buf = as_cstr_buf(expr);
    let msg_buf = as_cstr_buf(msg);
    let file_buf = as_cstr_buf(file);
    let func_buf = as_cstr_buf(func);

    unsafe {
        ffi::__fatal_error(
            expr_buf.as_ptr(),
            msg_buf.as_ptr(),
            file_buf.as_ptr(),
            line as i32,
            func_buf.as_ptr(),
        );
    }
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
        fn f() {}
        fn type_name_of<T>(_: T) -> &'static str {
            core::any::type_name::<T>()
        }
        let name = type_name_of(f);
        name.get(..name.len() - 3).unwrap_or("")
    }};
}

macro_rules! unwrap {
    ($e:expr, $msg:expr) => {{
        use crate::trezorhal::common::UnwrapOrFatalError;
        $e.unwrap_or_fatal_error("unwrap failed", $msg, file!(), line!(), function_name!())
    }};
    ($expr:expr) => {
        unwrap!($expr, "")
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
        crate::trezorhal::common::__fatal_error($expr, $msg, file!(), line!(), function_name!());
    }};
}

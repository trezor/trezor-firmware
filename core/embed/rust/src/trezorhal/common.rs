use cstr_core::CStr;

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

const NULL_TERMINATED_MAXLEN: usize = 50;

pub struct StackCStr([u8; NULL_TERMINATED_MAXLEN]);

impl StackCStr {
    pub fn new(s: &str) -> Self {
        let mut cstr = Self([0; NULL_TERMINATED_MAXLEN]);
        cstr.set_truncated(s);
        cstr
    }

    pub fn set_truncated(&mut self, s: &str) {
        let len = s.len().max(NULL_TERMINATED_MAXLEN - 1);
        self.0[..len].copy_from_slice(s.as_bytes());
        self.0[len] = 0;
    }

    pub fn cstr(&self) -> &CStr {
        unsafe { CStr::from_bytes_with_nul_unchecked(&self.0) }
    }
}

#[cfg(not(feature = "bootloader"))]
pub fn __fatal_error(expr: &CStr, msg: &CStr, file: &CStr, line: u32, func: &CStr) -> ! {
    unsafe {
        ffi::__fatal_error(
            expr.as_ptr(),
            msg.as_ptr(),
            file.as_ptr(),
            line as i32,
            func.as_ptr(),
        );
    }
}

#[cfg(feature = "bootloader")]
pub fn __fatal_error(_expr: &CStr, _msg: &CStr, _file: &CStr, _line: u32, _func: &CStr) -> ! {
    use core::ptr;
    use cstr_core::cstr;

    unsafe {
        ffi::__fatal_error(
            ptr::null(),
            cstr!("BL.rs").as_ptr(),
            ptr::null(),
            0,
            ptr::null(),
        );
    }
}

pub trait UnwrapOrFatalError<T> {
    fn unwrap_or_fatal_error(
        self,
        expr: &CStr,
        msg: &CStr,
        file: &CStr,
        line: u32,
        func: &CStr,
    ) -> T;
}

impl<T> UnwrapOrFatalError<T> for Option<T> {
    fn unwrap_or_fatal_error(
        self,
        expr: &CStr,
        msg: &CStr,
        file: &CStr,
        line: u32,
        func: &CStr,
    ) -> T {
        match self {
            Some(x) => x,
            None => __fatal_error(expr, msg, file, line, func),
        }
    }
}

impl<T, E> UnwrapOrFatalError<T> for Result<T, E> {
    fn unwrap_or_fatal_error(
        self,
        expr: &CStr,
        msg: &CStr,
        file: &CStr,
        line: u32,
        func: &CStr,
    ) -> T {
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
            use crate::trezorhal::common::StackCStr;

            fn f() {}
            fn type_name_of<T>(_: T) -> &'static str {
                core::any::type_name::<T>()
            }
            let name = type_name_of(f);
            let name_trunc = name.get(..name.len() - 3).unwrap_or("");
            StackCStr::new(name_trunc).cstr()
        }
        #[cfg(feature = "bootloader")]
        {
            cstr_core::cstr!("")
        }
    }};
}

macro_rules! unwrap {
    ($e:expr, $msg:literal) => {{
        use crate::trezorhal::common::UnwrapOrFatalError;
        use cstr_core::cstr;
        $e.unwrap_or_fatal_error(
            cstr!(stringify!($e)),
            cstr!($msg),
            cstr!(file!()),
            line!(),
            function_name!(),
        )
    }};
    ($expr:expr) => {
        unwrap!($expr, "unwrap failed")
    };
}

macro_rules! ensure {
    ($what:expr, $error:literal) => {
        if !($what) {
            fatal_error!(stringify!($what), $error);
        }
    };
}

macro_rules! fatal_error {
    ($expr:expr, $msg:literal) => {{
        use cstr_core::cstr;
        crate::trezorhal::common::__fatal_error(
            cstr!(stringify!($expr)),
            cstr!($msg),
            cstr!(file!()),
            line!(),
            function_name!(),
        );
    }};
}

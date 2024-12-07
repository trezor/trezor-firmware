mod ffi {
    extern "C" {
        // system.h
        pub fn system_exit_error_ex(
            title: *const cty::c_char,
            title_len: usize,
            message: *const cty::c_char,
            message_len: usize,
            footer: *const cty::c_char,
            footer_len: usize,
        ) -> !;
    }
}

pub fn error_shutdown(msg: &str) -> ! {
    unsafe {
        // SAFETY: we pass a valid string to the C function
        // and the function does not return.
        ffi::system_exit_error_ex(
            core::ptr::null(),
            0,
            msg.as_ptr() as *const cty::c_char,
            msg.len(),
            core::ptr::null(),
            0,
        );
    }
}

/// Shows an error message on the screen and shuts down the device.
/// In debug mode, also prints the error message to the console.
#[inline(never)] // saves few kilobytes of flash
pub fn __fatal_error(msg: &str, _file: &str, _line: u32) -> ! {
    #[cfg(feature = "debug")]
    {
        dbg_println!("=== FATAL ERROR");

        if _line != 0 {
            dbg_println!("Location: {}:{}", _file, _line);
        }
        if !msg.is_empty() {
            dbg_println!("Message: {}", msg);
        }

        dbg_println!("===");
    }

    error_shutdown(msg);
}

pub trait UnwrapOrFatalError<T> {
    fn unwrap_or_fatal_error(self, msg: &str, file: &str, line: u32) -> T;
}

impl<T> UnwrapOrFatalError<T> for Option<T> {
    fn unwrap_or_fatal_error(self, msg: &str, file: &str, line: u32) -> T {
        match self {
            Some(x) => x,
            None => __fatal_error(msg, file, line),
        }
    }
}

impl<T, E> UnwrapOrFatalError<T> for Result<T, E> {
    fn unwrap_or_fatal_error(self, msg: &str, file: &str, line: u32) -> T {
        match self {
            Ok(x) => x,
            Err(_) => __fatal_error(msg, file, line),
        }
    }
}

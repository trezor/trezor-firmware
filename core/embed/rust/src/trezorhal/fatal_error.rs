mod ffi {
    extern "C" {
        // bootutils.h
        pub fn error_shutdown(msg: *const cty::c_char) -> !;
    }
}

pub fn error_shutdown(msg: &str) -> ! {
    const MAX_LEN: usize = 63;
    let mut buffer: [u8; MAX_LEN + 1] = [0; MAX_LEN + 1];

    // Copy the message to the buffer
    let msg_bytes = msg.as_bytes();
    let len = if msg_bytes.len() < MAX_LEN { msg_bytes.len() } else { MAX_LEN };
    buffer[..len].copy_from_slice(&msg_bytes[..len]);

    unsafe {
        // SAFETY: `buffer` is a valid null-terminated string
        // and the function never returns.
        ffi::error_shutdown(buffer.as_ptr() as *const cty::c_char);
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

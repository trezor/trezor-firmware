mod ffi {
    extern "C" {
        // trezorhal/common.c
        pub fn trezor_shutdown() -> !;
    }
}

use crate::ui::{
    shape,
    ui_features::{ModelUI, UIFeaturesCommon},
};

fn shutdown() -> ! {
    unsafe { ffi::trezor_shutdown() }
}

/// Shows an error message and shuts down the device.
pub fn error_shutdown(title: &str, msg: &str, footer: &str) -> ! {
    // SAFETY:
    // This is the only situation we are allowed use this function
    // to allow nested calls to `run_with_bumps`/`render_on_display`,
    // because after the error message is displayed, the application will
    // shut down.
    unsafe { shape::unlock_bumps_on_failure() };

    ModelUI::screen_fatal_error(title, msg, footer);
    ModelUI::backlight_on();
    shutdown()
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

    error_shutdown("INTERNAL_ERROR", msg, "PLEASE VISIT\nTREZOR.IO/RSOD");
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

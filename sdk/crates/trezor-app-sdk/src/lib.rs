//! # Trezor App SDK
//!
//! A unified SDK for developing Trezor applications in Rust.
//!
//! This SDK provides:
//! - **Logging**: Structured logging with compile-time filtering
//! - **UI API**: High-level functions for user interaction (confirm dialogs, input, etc.)
//! - **Low-level API**: Direct access to system functions (internal use)
//!
//! ## Quick Start
//!
//! ```rust
//! use trezor_app_sdk::{info, error, ui};
//!
//! #[no_mangle]
//! pub extern "C" fn applet_main(api_get: trezor_app_sdk::TrezorApiGetter) -> i32 {
//!     // Initialize the SDK
//!     if let Err(e) = trezor_app_sdk::init(api_get) {
//!         return e.to_c_int();
//!     }
//!
//!     info!("Application started");
//!
//!     // Use high-level UI functions
//!     match ui::confirm_value("Title", "Confirm this action?") {
//!         Ok(true) => {
//!             info!("User confirmed");
//!             ui::show_success("Success", "Action completed")?;
//!         }
//!         Ok(false) => {
//!             info!("User cancelled");
//!         }
//!         Err(e) => {
//!             error!("UI error: {:?}", e);
//!             return e.to_c_int();
//!         }
//!     }
//!
//!     0
//! }
//! ```

#![no_std]
#![feature(core_intrinsics, alloc_error_handler, lang_items)]
#![allow(internal_features)]

extern crate alloc;

// Internal low-level API module
pub mod low_level_api;

// Public modules
pub mod log;
pub mod ui;

mod critical_section;

use alloc::format;
/// A wrapper which aligns its inner value to 4 bytes.
#[derive(Clone, Copy, Debug)]
#[repr(C, align(8))]
pub struct Align<T>(
    /// The inner value.
    pub T,
);

// Re-export logging macros at the root
pub use log::{Level, Logger, Record};

// Re-export UI archived types
pub use ui::{ArchivedTrezorUiEnum, ArchivedTrezorUiResult};

use crate::ui::request_finish;
use core::ffi::c_int;
use low_level_api::{Api, ApiWrapper, TrezorApiGetter, TREZOR_API_VERSION_1};

// The application provides an unmangled Rust function `app` that returns Result<()>
extern "Rust" {
    fn app() -> Result<()>;
}

/// Result type alias
pub use low_level_api::ApiError;
pub type Result<T> = core::result::Result<T, ApiError>;

// Logger implementation
struct AppLogger;

impl Logger for AppLogger {
    fn log(&self, record: &Record) {
        let timestamp = Api::systick_ms().unwrap_or(0);
        let formatted = format!(
            "[{:08}] {} [{}] {}\n",
            timestamp,
            record.level.as_str(),
            record.module,
            record.args
        );
        let _ = Api::dbg_console_write(formatted.as_bytes());
    }
}

// Register the global logger
#[no_mangle]
fn __trezor_log_global_logger() -> &'static dyn Logger {
    static LOGGER: AppLogger = AppLogger;
    &LOGGER
}

#[no_mangle]
pub extern "C" fn applet_main(api_get: TrezorApiGetter) -> c_int {
    if let Err(e) = Api::init(api_get, TREZOR_API_VERSION_1) {
        return e.to_c_int();
    }

    info!("Hello world!");

    let mut ipc_buffer = Align([0u8; 200]);

    info!("registering IPC");
    Api::ipc_register(1, &mut ipc_buffer.0[..]).unwrap();

    trace!("IPC registered");

    // Call the user's app function
    let result = unsafe { app() };
    info!("Finishing request");
    _ = request_finish();

    match result {
        Ok(()) => {
            info!("Application completed successfully");
            _ = Api::system_exit(0);
        }
        Err(e) => {
            let code = e.to_c_int();
            error!("Application failed with error code: {}", code);
            _ = Api::system_exit(code);
        }
    }

    0
}

#[panic_handler]
fn panic_handler(_: &core::panic::PanicInfo<'_>) -> ! {
    core::intrinsics::abort();
}

// #[alloc_error_handler]
// fn alloc_error_handler(_: alloc::alloc::Layout) -> ! {
//     core::intrinsics::abort();
// }

#[lang = "eh_personality"]
fn eh_personality() -> ! {
    loop {}
}

#[no_mangle]
unsafe extern "C" fn _Unwind_Resume() {
    core::intrinsics::unreachable();
}

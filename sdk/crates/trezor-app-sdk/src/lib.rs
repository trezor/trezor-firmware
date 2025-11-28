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
//! #[unsafe(no_mangle)]
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
#![allow(internal_features)]
#![feature(core_intrinsics)]
#![feature(lang_items)]

mod critical_section;
mod ipc;
// Internal low-level API module
mod low_level_api;
mod sysevent;

// Public modules
pub mod log;
pub mod print;
pub mod service;
pub mod ui;
pub mod util;

/// A wrapper which aligns its inner value to 4 bytes.
#[derive(Clone, Copy, Debug)]
#[repr(C, align(8))]
pub struct Align<T>(
    /// The inner value.
    pub T,
);

// Re-export UI archived types
pub use ui::{ArchivedTrezorUiEnum, ArchivedTrezorUiResult};

#[derive(ufmt::derive::uDebug)]
pub enum Error {
    ApiError(ApiError),
    ServiceError,
    InvalidFunction,
    InvalidMessage,
    Cancelled,
}

impl From<ApiError> for Error {
    fn from(error: ApiError) -> Self {
        Error::ApiError(error)
    }
}

impl From<service::Error<'_>> for Error {
    fn from(_error: service::Error) -> Self {
        Error::ServiceError
    }
}

// The application provides an unmangled Rust function `app` that returns Result<()>
unsafe extern "Rust" {
    unsafe fn app() -> Result<()>;
}

/// Result type alias
pub use low_level_api::ApiError;
pub type Result<T> = core::result::Result<T, Error>;
pub use ipc::IpcMessage;

static_service!(CORE_SERVICE, CoreApp, service::CoreIpcService, 2048);

#[unsafe(no_mangle)]
pub unsafe extern "C" fn applet_main(
    api_get: low_level_api::ffi::trezor_api_getter_t,
) -> cty::c_int {
    trace!("Initializing API");
    // SAFETY: trusting the caller of applet_main to provide us with a valid getter
    unsafe { low_level_api::init(api_get) };

    info!("registering IPC");
    CORE_SERVICE.start();
    ui::init(&CORE_SERVICE);
    trace!("IPC registered");

    // Call the user's app function
    let result = unsafe { app() };
    info!("Finishing request");

    match result {
        Ok(()) => {
            info!("Application completed successfully");
            _ = low_level_api::system_exit();
        }
        Err(e) => {
            let mut error_buf = [0u8; 256];
            let mut writer = util::SliceWriter::new(&mut error_buf);
            _ = ufmt::uwrite!(writer, "Application failed with error code: {:?}", e);
            error!("{}", writer.as_ref());
            _ = low_level_api::system_exit_error("Error", writer.as_ref(), "");
        }
    }
}

#[cfg(not(test))]
#[panic_handler]
fn panic_handler(info: &core::panic::PanicInfo<'_>) -> ! {
    low_level_api::system_exit_fatal(
        info.message().as_str().unwrap_or("PANIC"),
        info.location().map_or("<unknown>", |loc| &loc.file()[20..]),
        info.location().map_or(0, |loc| loc.line() as i32),
    );
}

#[cfg(not(test))]
#[lang = "eh_personality"]
fn eh_personality() -> ! {
    loop {}
}

#[unsafe(no_mangle)]
unsafe extern "C" fn _Unwind_Resume() {
    unsafe { core::intrinsics::unreachable() };
}

#[cfg(not(target_os = "none"))]
#[unsafe(no_mangle)]
pub extern "C" fn main() {}

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

#![cfg_attr(not(feature = "test"), no_std)]
#![allow(internal_features)]
#![allow(dead_code)]
#![feature(core_intrinsics)]
#![cfg_attr(
    all(feature = "debug", not(feature = "test")),
    feature(lang_items)
)]

#[cfg(all(feature = "debug", feature = "alloc"))]
extern crate alloc;
#[cfg(all(feature = "debug", feature = "alloc"))]
use alloc::boxed::Box;

mod critical_section;
mod ipc;
// Internal low-level API module
mod core_services;
mod low_level_api;
mod sysevent;

// Public modules
pub mod crypto;
pub mod log;
pub mod print;
pub mod service;
pub mod ui;
pub mod util;

#[cfg(feature = "test")]
pub mod mock;

#[macro_use]
pub mod macros;

/// A wrapper which aligns its inner value to 4 bytes.
#[repr(C, align(8))]
pub struct Align<T>(
    /// The inner value.
    pub T,
);

// Re-export UI archived types
pub use ui::{ArchivedTrezorUiEnum, ArchivedTrezorUiResult};

#[cfg_attr(
    any(all(feature = "debug", feature = "alloc"), feature = "test"),
    derive(Debug)
)]
pub enum Error {
    ApiError(ApiError),
    ServiceError,
    DataError(&'static str),
    Cancelled,
    InvalidFunction,
    InvalidMessage,
    InvalidArgument,
    ValueError(&'static str),
    #[cfg(all(feature = "debug", feature = "alloc"))]
    Context {
        context: &'static str,
        source: Box<Error>,
    },
}

impl Error {
    pub fn code(&self) -> u16 {
        match self {
            // Keep API error code space separate from local SDK errors.
            Self::ApiError(_) => 1,
            Self::ServiceError => 2,
            Self::DataError(_) => 3,
            Self::Cancelled => 4,
            Self::InvalidFunction => 5,
            Self::InvalidMessage => 6,
            Self::InvalidArgument => 7,
            Self::ValueError(_) => 8,
            #[cfg(all(feature = "debug", feature = "alloc"))]
            Self::Context { source, .. } => source.code(),
        }
    }

    pub fn message(&self) -> &'static str {
        match self {
            Self::ApiError(_) => "",
            Self::ServiceError => "",
            Self::InvalidFunction => "",
            Self::InvalidMessage => "",
            Self::InvalidArgument => "",
            Self::DataError(msg) => msg,
            Self::ValueError(msg) => msg,
            Self::Cancelled => "",
            #[cfg(all(feature = "debug", feature = "alloc"))]
            Self::Context { source, .. } => source.message(),
        }
    }

    pub fn error_type(&self) -> &'static str {
        match self {
            Self::ApiError(_) => "ApiError",
            Self::ServiceError => "ServiceError",
            Self::DataError(_) => "DataError",
            Self::Cancelled => "Cancelled",
            Self::InvalidFunction => "InvalidFunction",
            Self::InvalidMessage => "InvalidMessage",
            Self::InvalidArgument => "InvalidArgument",
            Self::ValueError(_) => "ValueError",
            #[cfg(all(feature = "debug", feature = "alloc"))]
            Self::Context { source, .. } => source.error_type(),
        }
    }

    #[cfg(all(feature = "debug", feature = "alloc"))]
    pub fn context(self, context: &'static str) -> Self {
        Error::Context {
            context,
            source: Box::new(self),
        }
    }
    #[cfg(not(all(feature = "debug", feature = "alloc")))]
    pub fn context(self, _context: &'static str) -> Self {
        self
    }

    #[cfg(all(feature = "debug", feature = "alloc"))]
    pub fn source(&self) -> Option<&Error> {
        match self {
            Error::Context { source, .. } => Some(&*source),
            _ => None,
        }
    }
}

#[cfg(all(feature = "debug", feature = "alloc"))]
impl ufmt::uDisplay for Error {
    fn fmt<W: ?Sized>(&self, f: &mut ufmt::Formatter<'_, W>) -> core::result::Result<(), W::Error>
    where
        W: ufmt::uWrite,
    {
        // Print the main error line
        match self {
            Error::Context { context, .. } => {
                ufmt::uwrite!(f, "{}", context)?;
            }
            _ => {
                ufmt::uwrite!(f, "{}: {}", self.error_type(), self.message())?;
            }
        }

        // Print the context chain
        let mut source = self.source();
        while let Some(err) = source {
            match err {
                Error::Context { context, .. } => {
                    ufmt::uwrite!(f, "\nCaused by: {}", context)?;
                }
                _ => {
                    ufmt::uwrite!(f, "\nCaused by: {}: {}", err.error_type(), err.message())?;
                }
            }
            source = err.source();
        }
        Ok(())
    }
}

#[cfg(not(all(feature = "debug", feature = "alloc")))]
impl ufmt::uDisplay for Error {
    fn fmt<W: ?Sized>(&self, f: &mut ufmt::Formatter<'_, W>) -> core::result::Result<(), W::Error>
    where
        W: ufmt::uWrite,
    {
        ufmt::uwrite!(f, "{}: {}", self.error_type(), self.message())?;
        Ok(())
    }
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

pub trait ResultExt<T> {
    fn context(self, context: &'static str) -> Self;
}

impl<T> ResultExt<T> for Result<T> {
    fn context(self, context: &'static str) -> Self {
        self.map_err(|e| e.context(context))
    }
}

// The application provides an unmangled Rust function `app` that returns Result<()>
#[cfg(not(feature = "test"))]
unsafe extern "Rust" {
    unsafe fn app() -> Result<()>;
}

/// Result type alias
pub use low_level_api::ApiError;

pub type Result<T> = core::result::Result<T, Error>;

pub use ipc::IpcMessage;

static_service!(CORE_SERVICE, CoreApp, service::CoreIpcService, 16384);

#[cfg(not(feature = "test"))]
#[unsafe(no_mangle)]
pub unsafe extern "C" fn applet_main(
    api_get: low_level_api::ffi::trezor_api_getter_t,
) -> core::ffi::c_int {
    // SAFETY: trusting the caller of applet_main to provide us with a valid getter
    unsafe { low_level_api::init(api_get) };

    CORE_SERVICE.start();
    core_services::init(&CORE_SERVICE);

    // Call the user's app function
    let result = unsafe { app() };

    match result {
        Ok(()) => {
            _ = low_level_api::system_exit();
        }
        Err(e) => {
            error!("Application error");
            let mut error_buf = [0u8; 256];
            let mut writer = util::SliceWriter::new(&mut error_buf);
            _ = ufmt::uwrite!(
                writer,
                "Application failed with error type: {} code: {} and message: {}",
                e.error_type(),
                e.code(),
                e.message()
            );
            error!("{}", e);
            _ = low_level_api::system_exit_error("Error", writer.as_ref(), "");
        }
    }
}

#[cfg(all(feature = "debug", not(feature = "test")))]
#[panic_handler]
fn panic_handler(info: &core::panic::PanicInfo<'_>) -> ! {
    let msg = info.message().as_str().unwrap_or("PANIC");
    let (file, line) = info
        .location()
        .map(|loc| {
            // Show only the file name, not the full path
            let file = loc.file();
            let file_short = file.rsplit('/').next().unwrap_or(file);
            (file_short, loc.line() as i32)
        })
        .unwrap_or(("<unknown>", 0));
    low_level_api::system_exit_fatal(msg, file, line);
}

#[cfg(all(feature = "debug", not(feature = "test")))]
#[lang = "eh_personality"]
fn eh_personality() -> ! {
    loop {}
}

#[cfg(all(feature = "debug", not(feature = "test")))]
#[unsafe(no_mangle)]
unsafe extern "C" fn _Unwind_Resume() {
    unsafe { core::intrinsics::unreachable() };
}

#[cfg(not(feature = "test"))]
#[cfg(not(target_os = "none"))]
#[unsafe(no_mangle)]
pub extern "C" fn main() {}

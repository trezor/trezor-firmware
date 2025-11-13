//! Low-level API module
//!
//! This module provides direct access to the Trezor firmware API.
//! Most applications should use the high-level `ui` module instead.
//!
//! This module is public but should only be used for:
//! - Implementing custom loggers
//! - Advanced IPC operations not covered by the high-level API

mod api;
mod ffi;

// Internal re-exports
// pub(crate) use ffi::*;
// pub(crate) use api::{Api, ApiWrapper, IpcMessage};

// Public exports for advanced usage (like custom loggers)
pub(crate) use api::{Api, ApiWrapper, IpcMessage};
pub(crate) use ffi::{sysevents_t, trezor_api_getter_t as TrezorApiGetter, TREZOR_API_VERSION_1};
pub use api::ApiError;

//! Low-level API module
//!
//! This module provides direct access to the Trezor firmware API.
//! Most applications should use the high-level `ui` module instead.
//!
//! This module is public but should only be used for:
//! - Implementing custom loggers
//! - Advanced IPC operations not covered by the high-level API

mod api;
pub(crate) mod ffi;

pub use api::*;

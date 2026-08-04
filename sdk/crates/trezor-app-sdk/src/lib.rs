//! # Trezor App SDK
//!
//! A `no_std` SDK for developing Trezor applications in Rust.
//!
//! ## Features
//!
//! - `app`: Enables full app runtime (heap allocation, IPC, UI, crypto, etc.)
//!          Required for extapps / standalone app binaries.
//! - `debug`: Enables debug logging and richer error context
//! - `test`: Enables std-based testing utilities
//! - `nightly`: Enables unstable (nightly-only) language/library features
//!              used by the default panic/abort machinery. Default-enabled;
//!              disable on stable toolchains to fall back to stable-compatible
//!              implementations.
//!
//! Without `app`, only `structs` (shared API types) are available — suitable
//! for the core app which only needs to work with the API structs.

#![cfg_attr(not(feature = "test"), no_std)]
#![allow(internal_features)]
#![allow(dead_code)]
#![cfg_attr(feature = "nightly", feature(core_intrinsics))]
#![cfg_attr(
    all(feature = "debug", not(feature = "test"), feature = "nightly"),
    feature(lang_items)
)]
#![warn(missing_docs)]

// Always available: shared API structs used by both core app and extapps
mod structs;

// Full app runtime — only compiled when `app` feature is enabled
#[cfg(feature = "app")]
mod alloc_types;
#[cfg(feature = "app")]
mod core_services;
#[cfg(feature = "app")]
mod critical_section;
#[cfg(feature = "app")]
mod ipc;
#[cfg(feature = "app")]
mod low_level_api;
#[cfg(feature = "app")]
mod sysevent;

#[cfg(not(feature = "app"))]
pub mod crypto {

    pub use crate::structs::{Slice, TrezorCryptoEnum, TrezorCryptoResultRef};
}

// Full crypto runtime — only when `app` feature is enabled
#[cfg(feature = "app")]
pub mod crypto;

#[cfg(not(feature = "app"))]
pub mod ui {
    pub use crate::structs::{
        Property, Slice, StrExt, StrSlice, TrezorProgressEnum, TrezorUiEnum, TrezorUiResult,
    };
}

// Full ui runtime — only when `app` feature is enabled
#[cfg(feature = "app")]
pub mod ui;

#[cfg(feature = "app")]
pub mod log;

#[doc(hidden)]
#[cfg(feature = "app")]
pub mod print;
#[cfg(feature = "app")]
pub mod service;
#[cfg(feature = "app")]
pub mod util;

#[cfg(feature = "app")]
#[macro_use]
#[doc(hidden)]
pub mod macros;

#[cfg(feature = "app")]
mod wire;

#[cfg(feature = "test")]
pub mod mock;

// Everything below requires the `app` feature
#[cfg(feature = "app")]
mod app_runtime;

#[cfg(feature = "app")]
pub use app_runtime::{Align, Error, Result, ResultExt};
#[cfg(feature = "app")]
pub use low_level_api::ApiError;
#[cfg(feature = "app")]
pub use wire::{
    WireDecode, WireEncode, WireRequest, wire_error_raw, wire_receive_wire_start, wire_request,
    wire_request_raw, wire_respond_raw,
};

#[cfg(feature = "app")]
crate::static_service!(CORE_SERVICE, CoreApp, service::CoreIpcService, 16384);

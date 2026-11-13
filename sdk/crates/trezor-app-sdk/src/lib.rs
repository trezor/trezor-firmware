//! # Trezor App SDK
//!
//! A `no_std` SDK for developing Trezor applications in Rust.
//!
//! ## Features
//!
//! - `app`: Enables full app runtime (heap allocation, IPC, UI, crypto, etc.)
//!          Required for extapps / standalone app binaries. Needs a nightly
//!          toolchain (`extern_item_impls`, for the [`app`] entry point).
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
#![cfg_attr(
    all(feature = "debug", not(feature = "test"), feature = "nightly"),
    feature(lang_items)
)]
#![cfg_attr(feature = "app", feature(extern_item_impls))]
#![warn(missing_docs)]

extern crate alloc;

#[cfg(feature = "app")]
/// The SDK's [`Error`] type and helpers to add context to results.
pub mod error;
// Always available: shared API structs used by both core app and extapps
pub mod structs;

#[cfg(feature = "app")]
/// The app runtime: the entry point, access to Core's API and the heap allocator.
pub mod app_runtime;

/// The stable-ABI traits and types shared with Core.
pub mod traits;

#[cfg(feature = "app")]
pub mod crypto;

#[cfg(feature = "app")]
pub mod ui;

#[cfg(feature = "app")]
pub mod log;

#[doc(hidden)]
#[cfg(feature = "app")]
pub mod print;

#[cfg(feature = "app")]
/// Small helpers, such as [`util::Timeout`].
pub mod util;

#[cfg(feature = "app")]
#[macro_use]
#[doc(hidden)]
pub mod macros;

#[cfg(feature = "app")]
mod wire;

#[cfg(feature = "app")]
mod codec;

#[cfg(feature = "test")]
pub mod mock;

#[cfg(feature = "app")]
pub use app_runtime::app;
#[cfg(feature = "app")]
pub use codec::{WireDecode, WireEncode, WireRequest, wire_request};
#[cfg(feature = "app")]
pub use error::{Error, IntoAppResult, Result, ResultExt, ServiceResultExt};
#[cfg(feature = "app")]
pub use wire::{wire_call, wire_error, wire_receive, wire_send};

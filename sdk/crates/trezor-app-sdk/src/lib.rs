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
//!
//! Without `app`, only `structs` (shared API types) are available — suitable
//! for the core app which only needs to work with the API structs.

#![cfg_attr(not(feature = "test"), no_std)]
#![allow(internal_features)]
#![allow(dead_code)]
#![feature(core_intrinsics)]
#![feature(allocator_api)]
#![feature(const_trait_impl)]
#![cfg_attr(all(feature = "debug", not(feature = "test")), feature(lang_items))]

#![feature(panic_internals)]

extern crate alloc;

pub mod error;
// Always available: shared API structs used by both core app and extapps
pub mod structs;

#[cfg(feature = "app")]
pub mod app_runtime2;

pub mod traits;

// Full app runtime — only compiled when `app` feature is enabled
#[cfg(feature = "app")]
mod core_services;
// #[cfg(feature = "app")]
// mod critical_section;
// #[cfg(feature = "app")]
// mod low_level_api;

// #[cfg(feature = "app")]
// pub mod alloc_types;
#[cfg(feature = "app")]
pub mod crypto;
#[cfg(feature = "app")]
pub mod log;
#[cfg(feature = "app")]
pub mod print;
#[cfg(feature = "app")]
pub mod ui;
#[cfg(feature = "app")]
pub mod util;

#[cfg(feature = "app")]
#[macro_use]
pub mod macros;

#[cfg(feature = "test")]
pub mod mock;

// Everything below requires the `app` feature
#[cfg(feature = "app")]
mod app_runtime;

#[cfg(feature = "app")]
pub use app_runtime::{Align, Error, Result, ResultExt};
#[cfg(feature = "app")]
pub use ui::{ArchivedTrezorUiEnum, ArchivedTrezorUiResult};

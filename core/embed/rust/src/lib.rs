#![cfg_attr(not(test), no_std)]
#![deny(clippy::all)]
#![deny(clippy::cast_lossless)]
#![allow(clippy::new_without_default)]
#![allow(clippy::ptr_offset_with_cast)] // workaround https://github.com/rust-lang/rust-bindgen/issues/3053
#![deny(unsafe_op_in_unsafe_fn)]
#![allow(internal_features)]
// Allowing dead code not to cause a lot of warnings when building for a specific target
// (when building for TR, a lot of code only used in TT would get marked as unused).
#![allow(dead_code)]
#![feature(lang_items)]
#![feature(trait_alias)]
#![feature(custom_test_frameworks)]
#![no_main]
#![reexport_test_harness_main = "test_main"]

#[macro_use]
extern crate num_derive;

#[macro_use]
mod macros;

mod align;
#[cfg(feature = "debug")]
mod coverage;
#[cfg(feature = "universal_fw")]
mod definitions;
mod error;
mod io;
mod maybe_trace;
#[cfg(feature = "micropython")]
mod micropython;
#[cfg(feature = "protobuf")]
mod protobuf;
#[cfg(feature = "storage")]
mod storage;
mod strutil;
#[cfg(feature = "thp")]
mod thp;
mod time;
#[cfg(feature = "ui_debug")]
mod trace;
#[cfg(feature = "translations")]
mod translations;
mod trezorhal;

// mod ui is `pub` because of the re-export pattern in individual models, which
// would trigger a brickload of "unused symbol" warnings otherwise.
// TODO: maybe get rid of the re-export pattern :shrugs:
#[cfg(feature = "ui")]
pub mod ui;

pub mod util;

#[cfg(feature = "bootloader")]
mod bootloader;

// pull in the unwrap! / ensure! / fatal_error! macros
#[macro_use]
extern crate rtl;

#[cfg(not(target_arch = "arm"))]
#[cfg(not(test))]
#[cfg(any(not(feature = "test"), feature = "clippy"))]
#[lang = "eh_personality"]
/// Needed by full debuginfo `opt-level = 0` builds for some reason.
extern "C" fn eh_personality() {}

#[cfg(test)]
#[no_mangle]
pub fn main() -> i32 {
    // Initialize the C driver code before running tests
    unsafe {
        extern "C" {
            fn rust_tests_c_setup();
        }
        rust_tests_c_setup();
    }

    match std::env::var("RUST_LOG") {
        Ok(s) if s != "0" => crate::util::logger::init_rust_logging(0),
        _ => eprintln!("Set RUST_LOG=1 to enable logs."),
    }

    // Call the Rust test harness main function
    // The function panics if any test fails.
    // Asserting that it returns () to ensure that if a future Rust version
    // changes the signature and behavior, we'll be notified.
    assert_eq!(test_main(), ());

    // Return 0 to indicate success
    0
}

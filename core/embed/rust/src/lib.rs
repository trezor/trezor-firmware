#![cfg_attr(not(test), no_std)]
#![deny(clippy::all)]
#![allow(clippy::new_without_default)]
#![deny(unsafe_op_in_unsafe_fn)]
#![allow(dead_code)]
#![feature(lang_items)]

#[macro_use]
extern crate num_derive;

mod error;
// use trezorhal for its macros early
#[macro_use]
mod trezorhal;
#[cfg(feature = "micropython")]
#[macro_use]
mod micropython;
#[cfg(feature = "protobuf")]
mod protobuf;
mod time;
#[cfg(feature = "ui_debug")]
mod trace;

#[cfg(feature = "ui")]
#[macro_use]
pub mod ui;

#[cfg(feature = "debug")]
#[panic_handler]
/// More detailed panic handling. The difference against
/// default `panic` below is that this "debug" version
/// takes around 10 kB more space in the flash region.
fn panic_debug(panic_info: &core::panic::PanicInfo) -> ! {
    // Filling at least the file and line information, if available.
    // TODO: find out how to display message from panic_info.message()
    if let Some(location) = panic_info.location() {
        trezorhal::common::__fatal_error("", "rs", location.file(), location.line(), "");
    } else {
        trezorhal::common::__fatal_error("", "rs", "", 0, "");
    }
}

#[cfg(not(feature = "debug"))]
#[cfg(not(test))]
#[cfg(any(not(feature = "test"), feature = "clippy"))]
#[panic_handler]
/// Default panic handling. Not showing any details - thus saving flash space.
fn panic(_info: &core::panic::PanicInfo) -> ! {
    // TODO: as of Rust 1.63 / nightly 2022-08, ignoring the `_info` parameter does
    // not help with saving flash space -- the `fmt` machinery still gets
    // compiled in. We can avoid that by using unstable Cargo arguments:
    //   -Zbuild-std=core -Zbuild-std-features=panic_immediate_abort
    // Doing that will compile every panic!() to a single udf instruction which
    // raises a Hard Fault on hardware.
    //
    // Otherwise, use `unwrap!` macro from trezorhal.
    trezorhal::common::__fatal_error("", "rs", "", 0, "");
}

#[cfg(not(target_arch = "arm"))]
#[cfg(not(test))]
#[cfg(any(not(feature = "test"), feature = "clippy"))]
#[lang = "eh_personality"]
/// Needed by full debuginfo `opt-level = 0` builds for some reason.
extern "C" fn eh_personality() {}

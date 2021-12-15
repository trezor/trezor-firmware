#![cfg_attr(not(test), no_std)]
#![deny(clippy::all)]
#![allow(clippy::new_without_default)]
#![deny(unsafe_op_in_unsafe_fn)]
#![allow(dead_code)]

mod error;
#[macro_use]
mod micropython;
mod protobuf;
#[cfg(feature = "ui_debug")]
mod trace;
mod trezorhal;

#[cfg(feature = "ui")]
#[macro_use]
mod ui;
mod util;

#[cfg(not(feature = "test"))]
#[panic_handler]
fn panic(_info: &core::panic::PanicInfo) -> ! {
    use cstr_core::CStr;

    // Although it would be ideal to use the original error message, ignoring it
    // lets us avoid the `fmt` machinery and its code size and is also important for
    // security reasons, as we do not always controls the message contents. We
    // should also avoid printing "panic" or "rust" on the user screen to avoid any
    // confusion.

    // SAFETY: Safe because we are passing in \0-terminated literals.
    let empty = unsafe { CStr::from_bytes_with_nul_unchecked(b"\0") };
    let msg = unsafe { CStr::from_bytes_with_nul_unchecked(b"rs\0") };

    // TODO: Ideally we would take the file and line info out of
    // `PanicInfo::location()`.
    trezorhal::common::fatal_error(empty, msg, empty, 0, empty);
}

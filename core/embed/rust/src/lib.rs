#![cfg_attr(not(test), no_std)]
#![deny(clippy::all)]
#![deny(unsafe_op_in_unsafe_fn)]
#![allow(dead_code)]

mod error;
#[macro_use]
mod micropython;
mod protobuf;
mod trezorhal;
mod util;

#[cfg(not(test))]
use core::panic::PanicInfo;
#[cfg(not(test))]
use cstr_core::CStr;

#[cfg(not(test))]
#[panic_handler]
fn panic(_info: &PanicInfo) -> ! {
    // Although it would be ideal to use the original error message, ignoring it
    // lets us avoid the `fmt` machinery and its code size and is also important for
    // security reasons, as we do not always controls the message contents. We
    // should also avoid printing "panic" or "rust" on the user screen to avoid any
    // confusion.

    // SAFETY: Safe because we are passing in \0-terminated literals.
    let empty = unsafe { CStr::from_bytes_with_nul_unchecked("\0".as_bytes()) };
    let msg = unsafe { CStr::from_bytes_with_nul_unchecked("rs\0".as_bytes()) };

    // TODO: Ideally we would take the file and line info out of
    // `PanicInfo::location()`.
    trezorhal::common::fatal_error(&empty, &msg, &empty, 0, &empty);
}

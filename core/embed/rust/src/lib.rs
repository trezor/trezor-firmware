#![no_std]
#![feature(never_type)]
#![feature(unsize)]
#![feature(coerce_unsized)]
#![feature(dispatch_from_dyn)]
#![deny(clippy::all)]
#![deny(unsafe_op_in_unsafe_fn)]
#![allow(dead_code)]

mod error;
#[macro_use]
mod micropython;
mod trezorhal;
mod util;

mod protobuf;
mod ui;

use core::panic::PanicInfo;
use cstr_core::CStr;

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

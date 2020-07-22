#![no_std]
#![feature(extern_types)]
#![deny(clippy::all)]

/// cbindgen:ignore
mod error;
/// cbindgen:ignore
mod micropython;
/// cbindgen:ignore
mod trezorhal;

mod ui;

use core::panic::PanicInfo;
use cstr_core::CStr;

#[panic_handler]
fn panic(_info: &PanicInfo) -> ! {
    // SAFETY: Safe because we are passing in \0-terminated literals.
    let empty = unsafe { CStr::from_bytes_with_nul_unchecked("\0".as_bytes()) };
    let msg = unsafe { CStr::from_bytes_with_nul_unchecked("rust\0".as_bytes()) };

    // TODO: Ideally we would take the file and line info out of
    // `PanicInfo::location()`.
    trezorhal::common::fatal_error(&empty, &msg, &empty, 0, &empty);
}

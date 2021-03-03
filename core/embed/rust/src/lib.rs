#![no_std]
#![feature(never_type)]
#![feature(unsize)]
#![feature(coerce_unsized)]
#![feature(dispatch_from_dyn)]
#![feature(once_cell)]
#![deny(clippy::all)]
#![allow(dead_code)]

mod error;
mod micropython;
mod trezorhal;
mod util;

mod protobuf;
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

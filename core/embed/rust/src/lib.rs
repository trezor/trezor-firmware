#![cfg_attr(not(test), no_std)]
#![deny(clippy::all)]
#![allow(clippy::new_without_default)]
#![deny(unsafe_op_in_unsafe_fn)]
#![allow(dead_code)]

mod error;
#[cfg(feature = "micropython")]
#[macro_use]
mod micropython;
#[cfg(feature = "protobuf")]
mod protobuf;
mod time;
#[cfg(feature = "ui_debug")]
mod trace;
mod trezorhal;

#[cfg(feature = "ui")]
#[macro_use]
pub mod ui;

#[cfg(feature = "debug")]
#[panic_handler]
/// More detailed panic handling. The difference against
/// default `panic` below is that this "debug" version
/// takes around 10 kB more space in the flash region.
fn panic_debug(panic_info: &core::panic::PanicInfo) -> ! {
    use cstr_core::CStr;

    // SAFETY: Safe because we are passing in \0-terminated literals.
    let empty = unsafe { CStr::from_bytes_with_nul_unchecked(b"\0") };
    let msg = unsafe { CStr::from_bytes_with_nul_unchecked(b"rs\0") };

    // Filling at least the file and line information, if available.
    // TODO: find out how to display message from panic_info.message()
    if let Some(location) = panic_info.location() {
        let file = location.file();
        let line = location.line();
        let mut file_str = heapless::String::<100>::from(file);
        file_str.push('\0').unwrap();
        let file_cstr = unsafe { CStr::from_bytes_with_nul_unchecked(file_str.as_bytes()) };
        trezorhal::common::fatal_error(empty, msg, file_cstr, line as _, empty);
    } else {
        trezorhal::common::fatal_error(empty, msg, empty, 0, empty);
    }
}

#[cfg(not(feature = "debug"))]
#[cfg(not(test))]
#[cfg(any(not(feature = "test"), feature = "clippy"))]
#[panic_handler]
/// Default panic handling. Not showing any details - thus saving flash space.
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

    trezorhal::common::fatal_error(empty, msg, empty, 0, empty);
}

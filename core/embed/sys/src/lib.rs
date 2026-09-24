#![no_std]

mod ffi;

pub mod irq;

// Compiled out for host-side unit tests, where std provides the handler.
// Cargo builds test targets and their dependencies with `panic = "unwind"`;
// all firmware and emulator profiles use `abort` or `immediate-abort`.
#[cfg(not(panic = "unwind"))]
mod panic;

#[cfg(feature = "dbg_console")]
pub mod syslog;

#[cfg(all(feature = "dbg_console", not(feature = "log_crate_disabled")))]
pub mod log_crate;

#[cfg(feature = "dbg_console")]
pub mod ulog;

pub mod time;

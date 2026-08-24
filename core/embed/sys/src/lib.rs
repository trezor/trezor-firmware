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

pub mod time;

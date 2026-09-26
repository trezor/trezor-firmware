#![no_std]

mod ffi;

#[cfg(feature = "ipc")]
pub mod ipc;
pub mod irq;

// Compiled out for host-side unit tests, where std provides the handler.
// Cargo builds test targets and their dependencies with `panic = "unwind"`;
// all firmware and emulator profiles use `abort` or `immediate-abort`.
#[cfg(not(panic = "unwind"))]
mod panic;

pub mod sysevent;

#[cfg(feature = "dbg_console")]
pub mod syslog;

pub mod time;

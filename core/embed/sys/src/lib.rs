#![no_std]

mod ffi;

pub mod irq;
#[cfg(feature = "dbg_console")]
pub mod syslog;

pub mod time;

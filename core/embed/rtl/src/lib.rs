#![no_std]

mod ffi;

pub mod error;
pub mod util;

pub use error::{system_exit_error, system_exit_fatal};

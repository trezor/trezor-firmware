#![no_std]

mod ffi;

pub mod error;
pub mod sysexit;
pub mod util;

pub use sysexit::{system_exit_error, system_exit_fatal};

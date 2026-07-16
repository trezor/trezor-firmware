#![no_std]

mod ffi;

pub mod error;
pub mod util;

pub use error::{__fatal_error, error_shutdown};

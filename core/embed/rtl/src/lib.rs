#![no_std]

mod cslice;
mod ffi;

pub mod error;
pub mod sysexit;

pub use cslice::CSlice;
pub use sysexit::{system_exit_error, system_exit_fatal};

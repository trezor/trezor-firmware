#![cfg_attr(not(test), no_std)]
#![feature(const_trait_impl)]

#[macro_use]
mod error_util;

#[macro_use]
#[allow(unused_macros)]
pub mod macros;

pub mod buffer;
pub mod dict;
pub mod error;
pub mod ffi;
pub mod func;
pub mod gc;
pub mod iter;
pub mod list;
pub mod map;
pub mod module;
pub mod obj;
pub mod print;
pub mod qstr;
pub mod py_object;
pub mod runtime;
pub mod simple_type;
pub mod typ;
pub mod util;

#[cfg(test)]
pub mod testutil;

pub use obj::Obj;
pub use error::Error;

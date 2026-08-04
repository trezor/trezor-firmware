#[cfg(not(feature = "test"))]
extern crate alloc;

#[cfg(all(not(feature = "test"), feature = "debug"))]
pub(crate) use alloc::boxed::Box;
#[cfg(not(feature = "test"))]
pub(crate) use alloc::{string::String, vec::Vec};
#[cfg(all(feature = "test", feature = "debug"))]
pub(crate) use std::boxed::Box;
#[cfg(feature = "test")]
pub(crate) use std::{string::String, vec::Vec};

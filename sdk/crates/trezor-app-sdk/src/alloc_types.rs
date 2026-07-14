#[cfg(not(feature = "test"))]
extern crate alloc;

#[cfg(not(feature = "test"))]
pub(crate) use alloc::{string::String, vec::Vec};
#[cfg(feature = "test")]
pub(crate) use std::{string::String, vec::Vec};

#[cfg(not(test))]
pub(crate) use alloc::{string::String, vec::Vec};
#[cfg(test)]
pub(crate) use std::{string::String, vec::Vec};

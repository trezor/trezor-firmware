//! Trezor Host Protocol implementation in Rust.

#![forbid(unsafe_code)]

pub mod alternating_bit;
mod control_byte;
mod crc32;
pub mod error;
pub mod fragment;
pub mod header;

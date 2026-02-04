#![doc = include_str!("../README.md")]
#![forbid(unsafe_code)]
#![cfg_attr(not(feature = "use_std"), no_std)]

mod alternating_bit;
pub mod channel;
mod control_byte;
mod crc32;
pub mod credential;
pub mod error;
pub mod fragment;
pub mod header;

pub use channel::{Backend, Channel, ChannelIO};
pub use error::Error;

pub trait Role: Clone + PartialEq {
    fn is_host() -> bool;
}

#[cfg_attr(any(test, debug_assertions), derive(Debug))]
#[derive(Clone, PartialEq, Eq)]
pub struct Host;

impl Role for Host {
    fn is_host() -> bool {
        true
    }
}

#[cfg_attr(any(test, debug_assertions), derive(Debug))]
#[derive(Clone, PartialEq, Eq)]
pub struct Device;

impl Role for Device {
    fn is_host() -> bool {
        false
    }
}

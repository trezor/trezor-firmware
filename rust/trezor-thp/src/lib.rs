#![doc = include_str!("../README.md")]
#![no_std]
#![forbid(unsafe_code)]

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
#[derive(Clone, PartialEq)]
pub struct Host;

impl Role for Host {
    fn is_host() -> bool {
        true
    }
}

#[cfg_attr(any(test, debug_assertions), derive(Debug))]
#[derive(Clone, PartialEq)]
pub struct Device;

impl Role for Device {
    fn is_host() -> bool {
        false
    }
}

extern crate alloc;

use ufmt::derive::uDebug;

use crate::sysevent::SysEvents;
use crate::{log, low_level_api};

#[derive(uDebug, Copy, Clone, PartialEq, Eq)]
pub struct Timeout(u32);

pub const TIMEOUT_MAX: u32 = u32::MAX / 2 - 1;

impl Timeout {
    pub fn ms(ms: u32) -> Self {
        assert!(ms <= TIMEOUT_MAX, "Timeout too long");
        Self(ms)
    }

    pub fn seconds(seconds: u32) -> Self {
        Self::ms(seconds * 1000)
    }

    pub fn minutes(minutes: u32) -> Self {
        Self::seconds(minutes * 60)
    }

    pub fn max() -> Self {
        Self::ms(TIMEOUT_MAX)
    }

    pub fn as_deadline(&self) -> u32 {
        low_level_api::systick_ms().wrapping_add(self.0)
    }

    pub fn sleep(&self) {
        let awaited = SysEvents::empty();
        awaited.poll(*self);
    }
}

pub struct SliceWriter<'a> {
    slice: &'a mut [u8],
    pos: usize,
}

impl<'a> SliceWriter<'a> {
    pub fn new(slice: &'a mut [u8]) -> Self {
        Self { slice, pos: 0 }
    }
}

impl<'a> ufmt::uWrite for SliceWriter<'a> {
    type Error = ();

    fn write_str(&mut self, s: &str) -> Result<(), Self::Error> {
        if self.pos + s.len() > self.slice.len() {
            return Err(());
        }
        self.slice[self.pos..self.pos + s.len()].copy_from_slice(s.as_bytes());
        self.pos += s.len();
        Ok(())
    }
}

impl<'a> AsRef<str> for SliceWriter<'a> {
    fn as_ref(&self) -> &str {
        // SAFETY: The only way to write is by invoking the ufmt::uWrite impl,
        // which appends valid Rust &strs.
        unsafe { core::str::from_utf8_unchecked(&self.slice[..self.pos]) }
    }
}

pub struct HdNodeData {
    pub depth: u32,
    pub fingerprint: u32,
    pub child_num: u32,
    pub chain_code: [u8; 32],
    pub public_key: [u8; 33],
}

pub fn hdnode_deserialize_public(serialized: &str, version: u32) -> Result<HdNodeData, i32> {
    let mut node_data = [0u8; 82];

    let decoded = bs58::decode(serialized).onto(&mut node_data).unwrap();
    if decoded != 82 {
        return Err(-1); // decode failed
    }

    log::info!("decoded len {}", decoded);

    // Check version
    let ver = u32::from_be_bytes(node_data[0..4].try_into().unwrap());
    if ver != version {
        return Err(-3); // invalid version
    }

    // Extract fields from node_data
    let depth = node_data[4];
    let fingerprint = u32::from_be_bytes(node_data[5..9].try_into().unwrap());
    let child_num = u32::from_be_bytes(node_data[9..13].try_into().unwrap());

    let mut chain_code = [0u8; 32];
    chain_code.copy_from_slice(&node_data[13..45]);

    let mut public_key = [0u8; 33];
    public_key.copy_from_slice(&node_data[45..78]);

    Ok(HdNodeData {
        depth: depth as u32,
        fingerprint,
        child_num,
        chain_code,
        public_key,
    })
}

pub fn hex_encode(bytes: &[u8]) -> alloc::string::String {
    use alloc::string::String;
    let mut result = String::new();
    for byte in bytes {
        // Manually append hex digits
        let high = (byte >> 4) & 0x0F;
        let low = byte & 0x0F;
        result.push(char::from_digit(high as u32, 16).unwrap());
        result.push(char::from_digit(low as u32, 16).unwrap());
    }
    result
}

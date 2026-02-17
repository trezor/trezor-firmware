extern crate alloc;

use ufmt::derive::uDebug;

use crate::low_level_api;
use crate::sysevent::SysEvents;

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

impl HdNodeData {
    const TOTAL: usize = 82;
    const VERSION_LEN: usize = 4;
    const VERSION_OFFSET: usize = 0;
    const DEPTH_LEN: usize = 1;
    const DEPTH_OFFSET: usize = HdNodeData::VERSION_LEN;
    const FINGERPRINT_LEN: usize = 4;
    const FINGERPRINT_OFFSET: usize = HdNodeData::DEPTH_OFFSET + HdNodeData::DEPTH_LEN;
    const CHILD_NUM_LEN: usize = 4;
    const CHILD_NUM_OFFSET: usize = HdNodeData::FINGERPRINT_OFFSET + HdNodeData::FINGERPRINT_LEN;
    const CHAIN_CODE_LEN: usize = 32;
    const CHAIN_CODE_OFFSET: usize = HdNodeData::CHILD_NUM_OFFSET + HdNodeData::CHILD_NUM_LEN;
    const PUBLIC_KEY_LEN: usize = 33;
    const PUBLIC_KEY_OFFSET: usize = HdNodeData::CHAIN_CODE_OFFSET + HdNodeData::CHAIN_CODE_LEN;

    pub fn deserialize_public(serialized: &str, version: u32) -> Result<Self, ()> {
        let mut node_data = [0u8; 82];

        // Decode base58 string
        let decoded_len = bs58::decode(serialized)
            .onto(&mut node_data)
            .map_err(|_| ())?;
        if decoded_len != Self::TOTAL {
            // TODO: decode failed or invalid length
            return Err(());
        }

        // Check version
        let ver = u32::from_be_bytes(
            node_data[Self::VERSION_OFFSET..Self::VERSION_OFFSET + Self::VERSION_LEN]
                .try_into()
                .map_err(|_| ())?,
        );
        if ver != version {
            // TODO: invalid version
            return Err(());
        }

        // Extract fields from node_data
        let depth = u8::from_be_bytes(
            node_data[Self::DEPTH_OFFSET..Self::DEPTH_OFFSET + Self::DEPTH_LEN]
                .try_into()
                .map_err(|_| ())?,
        );
        let fingerprint = u32::from_be_bytes(
            node_data[Self::FINGERPRINT_OFFSET..Self::FINGERPRINT_OFFSET + Self::FINGERPRINT_LEN]
                .try_into()
                .map_err(|_| ())?,
        );
        let child_num = u32::from_be_bytes(
            node_data[Self::CHILD_NUM_OFFSET..Self::CHILD_NUM_OFFSET + Self::CHILD_NUM_LEN]
                .try_into()
                .map_err(|_| ())?,
        );

        let mut chain_code = [0u8; Self::CHAIN_CODE_LEN];
        chain_code.copy_from_slice(
            &node_data[Self::CHAIN_CODE_OFFSET..Self::CHAIN_CODE_OFFSET + Self::CHAIN_CODE_LEN],
        );

        let mut public_key = [0u8; Self::PUBLIC_KEY_LEN];
        public_key.copy_from_slice(
            &node_data[Self::PUBLIC_KEY_OFFSET..Self::PUBLIC_KEY_OFFSET + Self::PUBLIC_KEY_LEN],
        );
        Ok(HdNodeData {
            depth: depth as u32,
            fingerprint,
            child_num,
            chain_code,
            public_key,
        })
    }
}

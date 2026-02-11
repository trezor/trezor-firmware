extern crate alloc;

use ufmt::derive::uDebug;

use crate::sysevent::SysEvents;
use crate::{HDNode, bignum256, curve_info, ecdsa_curve, low_level_api};

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

pub fn hdnode_deserialize_public(serialized: &str, version: u32) -> Result<(HDNode, u32), ()> {
    let mut params = ecdsa_curve {
        prime: bignum256 { val: [0u32; 9] },
        G: crate::low_level_api::ffi::curve_point {
            x: bignum256 { val: [0u32; 9] },
            y: bignum256 { val: [0u32; 9] },
        },
        order: bignum256 { val: [0u32; 9] },
        order_half: bignum256 { val: [0u32; 9] },
        a: 0,
        b: bignum256 { val: [0u32; 9] },
    };

    let curve_info = curve_info {
        bip32_name: b"secp256k1\0".as_ptr() as *const core::ffi::c_char,
        params: &params,
        hasher_base58: 0,
        hasher_sign: 0,
        hasher_pubkey: 0,
        hasher_script: 0,
    };

    let mut node = HDNode {
        depth: 0,
        child_num: 0,
        chain_code: [0u8; 32],
        private_key: [0u8; 32],
        public_key: [0u8; 33],
        private_key_extension: [0u8; 32],
        is_public_key_set: false,
        curve: &curve_info,
    };
    let mut fingerprint: u32 = 0;
    let result = low_level_api::hdnode_deserialize_public(
        serialized.as_ptr() as *const core::ffi::c_char,
        version,
        b"secp256k1\0".as_ptr() as *const core::ffi::c_char,
        &mut node,
        &mut fingerprint,
    );
    if result == 0 {
        Ok((node, fingerprint))
    } else {
        Err(())
    }
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

use core::ops::DerefMut;
use core::pin::Pin;

use super::ffi;
use super::memory::Memory;
use crate::hasher::{PinnedHasher, RawHasher};
use crate::init_ctx;
use crate::memory::ZeroableMemory;

pub const DIGEST_SIZE: usize = ffi::SHA256_DIGEST_LENGTH as usize;
pub type Digest = [u8; DIGEST_SIZE];

pub type HmacSha256Ctx = ffi::HMAC_SHA256_CTX;

unsafe impl ZeroableMemory for HmacSha256Ctx {}

impl HmacSha256Ctx {
    pub unsafe fn init_raw(&mut self, key: &[u8]) {
        unsafe { ffi::hmac_sha256_Init(self, key.as_ptr(), key.len() as u32) };
    }
}

impl RawHasher for Memory<HmacSha256Ctx> {
    type Digest = Digest;

    unsafe fn update_raw(&mut self, data: &[u8]) {
        unsafe { ffi::hmac_sha256_Update(self.as_mut(), data.as_ptr(), data.len() as u32) };
    }

    unsafe fn finalize_raw(&mut self) -> Self::Digest {
        let mut digest = [0u8; DIGEST_SIZE];
        unsafe { ffi::hmac_sha256_Final(self.as_mut(), digest.as_mut_ptr()) };
        digest
    }
}

pub fn hmac_sha256_new<D: DerefMut<Target = Memory<HmacSha256Ctx>>>(
    mut ctx: Pin<D>,
    key: &[u8],
) -> PinnedHasher<D> {
    let mut mut_ctx = ctx.as_mut();
    unsafe {
        // SAFETY: init_raw does not invalidate the pin
        mut_ctx.inner().init_raw(key);
        // SAFETY: context is initialized
        PinnedHasher::new_no_init(ctx)
    }
}

pub fn digest(key: &[u8], data: &[u8]) -> Digest {
    init_ctx!(ctx);
    let mut hmac = hmac_sha256_new(ctx, key);
    hmac.update(data);
    hmac.finalize()
}

#[cfg(test)]
mod test {
    use super::*;

    const HMAC_SHA256_EMPTY: &str =
        "b613679a0814d9ec772f95d778c35fc5ff1697c493715653c6c712144292c5ad";
    // RFC 4231
    const HMAC_SHA256_VECTORS: &[(&[u8], &[u8], &str)] = &[
        (
            &[0x0b; 20],
            b"Hi There",
            "b0344c61d8db38535ca8afceaf0bf12b881dc200c9833da726e9376c2e32cff7",
        ),
        (
            b"Jefe",
            b"what do ya want for nothing?",
            "5bdcc146bf60754e6a042426089575c75a003f089d2739839dec58b964ec3843",
        ),

        (
            &[0xaa; 20],
            &[0xdd; 50],
            "773ea91e36800e46854db8ebd09181a72959098b3ef8c122d9635514ced565fe",
        ),
        (
            &[0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f, 0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17, 0x18, 0x19],
            &[0xcd; 50],
            "82558a389a443c0ea4cc819899f2083a85f0faa3e578f8077a2e3ff46729665b",
        ),
        // skipping case with truncation
        (
            &[0xaa; 131],
            b"Test Using Larger Than Block-Size Key - Hash Key First",
            "60e431591ee0b67f0d8a26aacbf5b77f8e0bc6213728c5140546040f0ee37f54",
        ),
        (
            &[0xaa; 131],
            b"This is a test using a larger than block-size key and a larger than block-size data. The key needs to be hashed before being used by the HMAC algorithm.",
            "9b09ffa71b942fcb27635fbcd5b0e944bfdc63644f0713938a7f51535c3a35e2",
        ),
        (
            b"",
            b"",
            HMAC_SHA256_EMPTY,
        ),
    ];

    fn hexdigest(key: &[u8], data: &[u8]) -> String {
        hex::encode(digest(key, data))
    }

    #[test]
    fn test_empty_ctx() {
        init_ctx!(ctx);
        let mut ctx = hmac_sha256_new(ctx, b"");
        let out = ctx.finalize();
        let out_hex = hex::encode(out);

        assert_eq!(out_hex, HMAC_SHA256_EMPTY);
    }

    #[test]
    fn test_vectors() {
        for (key, data, expected) in HMAC_SHA256_VECTORS {
            let out_hex = hexdigest(key, data);
            assert_eq!(out_hex, *expected);
        }
    }

    #[test]
    fn test_update() {
        // case 3
        let key =
            b"\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa";
        init_ctx!(ctx);
        let mut ctx = hmac_sha256_new(ctx, key);
        for _ in 0..50 {
            ctx.update(b"\xdd");
        }
        let out = ctx.finalize();
        assert_eq!(
            hex::encode(out),
            "773ea91e36800e46854db8ebd09181a72959098b3ef8c122d9635514ced565fe"
        );

        // case 4
        let key = b"\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19";
        init_ctx!(ctx);
        let mut ctx = hmac_sha256_new(ctx, key);
        for _ in 0..50 {
            ctx.update(b"\xcd");
        }
        let out = ctx.finalize();
        assert_eq!(
            hex::encode(out),
            "82558a389a443c0ea4cc819899f2083a85f0faa3e578f8077a2e3ff46729665b"
        );
    }
}

use core::pin::Pin;

use zeroize::Zeroize as _;

use super::{
    ffi,
    memory::{init_ctx, Memory},
};

pub const DIGEST_SIZE: usize = ffi::SHA256_DIGEST_LENGTH as usize;
pub type Digest = [u8; DIGEST_SIZE];

pub struct HmacSha256<'a> {
    ctx: Pin<&'a mut Memory<ffi::HMAC_SHA256_CTX>>,
}

impl<'a> HmacSha256<'a> {
    pub fn new(mut ctx: Pin<&'a mut Memory<ffi::HMAC_SHA256_CTX>>, key: &[u8]) -> Self {
        // initialize the context
        // SAFETY: ffi
        unsafe { ffi::hmac_sha256_Init(ctx.inner(), key.as_ptr(), key.len() as u32) };
        Self { ctx }
    }

    pub fn update(&mut self, data: &[u8]) {
        // SAFETY: ffi
        unsafe { ffi::hmac_sha256_Update(self.ctx.inner(), data.as_ptr(), data.len() as u32) };
    }

    pub fn memory() -> Memory<ffi::HMAC_SHA256_CTX> {
        Memory::default()
    }

    pub fn finalize_into(mut self, out: &mut Digest) {
        // SAFETY: ffi
        unsafe { ffi::hmac_sha256_Final(self.ctx.inner(), out.as_mut_ptr()) };
    }
}

impl Drop for HmacSha256<'_> {
    fn drop(&mut self) {
        self.ctx.zeroize();
    }
}

pub fn digest_into(key: &[u8], data: &[u8], out: &mut Digest) {
    init_ctx!(HmacSha256, ctx, key);
    ctx.update(data);
    ctx.finalize_into(out);
}

pub fn digest(key: &[u8], data: &[u8]) -> Digest {
    let mut out = [0u8; DIGEST_SIZE];
    digest_into(key, data, &mut out);
    out
}

#[cfg(test)]
mod test {
    use crate::strutil::hexlify;

    use super::*;

    const HMAC_SHA256_EMPTY: &[u8] =
        b"b613679a0814d9ec772f95d778c35fc5ff1697c493715653c6c712144292c5ad";
    // RFC 4231
    const HMAC_SHA256_VECTORS: &[(&[u8], &[u8], &[u8])] = &[
        (
            &[0x0b; 20],
            b"Hi There",
            b"b0344c61d8db38535ca8afceaf0bf12b881dc200c9833da726e9376c2e32cff7",
        ),
        (
            b"Jefe",
            b"what do ya want for nothing?",
            b"5bdcc146bf60754e6a042426089575c75a003f089d2739839dec58b964ec3843",
        ),

        (
            &[0xaa; 20],
            &[0xdd; 50],
            b"773ea91e36800e46854db8ebd09181a72959098b3ef8c122d9635514ced565fe",
        ),
        (
            &[0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f, 0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17, 0x18, 0x19],
            &[0xcd; 50],
            b"82558a389a443c0ea4cc819899f2083a85f0faa3e578f8077a2e3ff46729665b",
        ),
        // skipping case with truncation
        (
            &[0xaa; 131],
            b"Test Using Larger Than Block-Size Key - Hash Key First",
            b"60e431591ee0b67f0d8a26aacbf5b77f8e0bc6213728c5140546040f0ee37f54",
        ),
        (
            &[0xaa; 131],
            b"This is a test using a larger than block-size key and a larger than block-size data. The key needs to be hashed before being used by the HMAC algorithm.",
            b"9b09ffa71b942fcb27635fbcd5b0e944bfdc63644f0713938a7f51535c3a35e2",
        ),
        (
            b"",
            b"",
            HMAC_SHA256_EMPTY,
        ),
    ];

    fn hexdigest(key: &[u8], data: &[u8]) -> [u8; DIGEST_SIZE * 2] {
        let mut out_hex = [0u8; DIGEST_SIZE * 2];

        let digest = digest(key, data);
        hexlify(&digest, &mut out_hex);
        out_hex
    }

    #[test]
    fn test_empty_ctx() {
        let mut out = [0u8; DIGEST_SIZE];
        let mut out_hex = [0u8; DIGEST_SIZE * 2];

        init_ctx!(HmacSha256, ctx, b"");
        ctx.finalize_into(&mut out);
        hexlify(&out, &mut out_hex);

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
        init_ctx!(HmacSha256, ctx, key);
        for _ in 0..50 {
            ctx.update(b"\xdd");
        }
        let mut out = [0u8; DIGEST_SIZE];
        ctx.finalize_into(&mut out);
        assert_eq!(
            hex::encode(out),
            "773ea91e36800e46854db8ebd09181a72959098b3ef8c122d9635514ced565fe"
        );

        // case 4
        let key = b"\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19";
        init_ctx!(HmacSha256, ctx, key);
        for _ in 0..50 {
            ctx.update(b"\xcd");
        }
        ctx.finalize_into(&mut out);
        assert_eq!(
            hex::encode(out),
            "82558a389a443c0ea4cc819899f2083a85f0faa3e578f8077a2e3ff46729665b"
        );
    }
}

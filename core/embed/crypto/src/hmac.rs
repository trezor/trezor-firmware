use core::ops::DerefMut;

use rtl::CSlice;

use super::ffi;
use super::secret::{HazardGuard, SecretContext, SecretContextLock, ZeroableMemory};

pub const DIGEST_SIZE: usize = ffi::SHA256_DIGEST_LENGTH as usize;
pub type Digest = [u8; DIGEST_SIZE];

pub const DIGEST_SIZE_512: usize = ffi::SHA512_DIGEST_LENGTH as usize;
pub type Digest512 = [u8; DIGEST_SIZE_512];

pub type HmacSha256Ctx = SecretContext<ffi::HMAC_SHA256_CTX>;
pub type HmacSha256Guard<'a> = HazardGuard<'a, ffi::HMAC_SHA256_CTX>;

// SAFETY: HMAC_SHA256_CTX is valid when zeroed
unsafe impl ZeroableMemory for ffi::HMAC_SHA256_CTX {}

impl HmacSha256Guard<'_> {
    /// Initialize the HMAC context with the given key.
    ///
    /// Called by [`HmacSha256::new`].
    pub fn init(&mut self, key: &[u8]) {
        let ptr = CSlice::from(key);
        // SAFETY: ffi
        // COPY HAZARD: operates on the guarded context in place
        unsafe { ffi::hmac_sha256_Init(self.hazard_mut(), ptr.ptr(), ptr.len() as u32) };
    }

    /// Update the HMAC context with the given data.
    pub fn update(&mut self, data: &[u8]) {
        let ptr = CSlice::from(data);
        // SAFETY: ffi
        // COPY HAZARD: operates on the guarded context in place
        unsafe { ffi::hmac_sha256_Update(self.hazard_mut(), ptr.ptr(), ptr.len() as u32) };
    }

    /// Finalize the HMAC context and return the digest.
    pub fn finalize(&mut self) -> Digest {
        let mut digest = [0u8; DIGEST_SIZE];
        // SAFETY: ffi
        // COPY HAZARD: operates on the guarded context in place
        unsafe { ffi::hmac_sha256_Final(self.hazard_mut(), digest.as_mut_ptr()) };
        digest
    }
}

/// HMAC-SHA256 hasher.
///
/// A wrapper around an HMAC-SHA256 context that provides a safe interface for
/// authenticating data.
pub struct HmacSha256<D: DerefMut<Target = HmacSha256Ctx>>(SecretContextLock<D>);

impl<D: DerefMut<Target = HmacSha256Ctx>> HmacSha256<D> {
    /// Construct a new HMAC-SHA256 hasher keyed by `key`.
    pub fn new(ctx: D, key: &[u8]) -> Self {
        let mut locked_ctx = SecretContextLock::new(ctx);
        locked_ctx.guarded().init(key);
        Self(locked_ctx)
    }

    /// Update the HMAC context with the given data.
    pub fn update(&mut self, data: &[u8]) {
        self.0.guarded().update(data);
    }

    /// Finalize the HMAC context and return the digest.
    pub fn finalize(mut self) -> Digest {
        self.0.guarded().finalize()
    }
}

impl HmacSha256<&'_ mut HmacSha256Ctx> {
    /// Calculate the HMAC-SHA256 digest of `data` under `key`.
    pub fn digest(key: &[u8], data: &[u8]) -> Digest {
        let mut ctx = HmacSha256Ctx::default();
        let mut hmac = HmacSha256::new(&mut ctx, key);
        hmac.update(data);
        hmac.finalize()
    }
}

pub type HmacSha512Ctx = SecretContext<ffi::HMAC_SHA512_CTX>;
pub type HmacSha512Guard<'a> = HazardGuard<'a, ffi::HMAC_SHA512_CTX>;

// SAFETY: HMAC_SHA512_CTX is valid when zeroed
unsafe impl ZeroableMemory for ffi::HMAC_SHA512_CTX {}

impl HmacSha512Guard<'_> {
    /// Initialize the HMAC context with the given key.
    pub fn init(&mut self, key: &[u8]) {
        let ptr = CSlice::from(key);
        // SAFETY: ffi
        // COPY HAZARD: operates on the guarded context in place
        unsafe { ffi::hmac_sha512_Init(self.hazard_mut(), ptr.ptr(), ptr.len() as u32) };
    }

    /// Update the HMAC context with the given data.
    pub fn update(&mut self, data: &[u8]) {
        let ptr = CSlice::from(data);
        // SAFETY: ffi
        // COPY HAZARD: operates on the guarded context in place
        unsafe { ffi::hmac_sha512_Update(self.hazard_mut(), ptr.ptr(), ptr.len() as u32) };
    }

    /// Finalize the HMAC context and return the digest.
    pub fn finalize(&mut self) -> Digest512 {
        let mut digest = [0u8; DIGEST_SIZE_512];
        // SAFETY: ffi
        // COPY HAZARD: operates on the guarded context in place
        unsafe { ffi::hmac_sha512_Final(self.hazard_mut(), digest.as_mut_ptr()) };
        digest
    }
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
        hex::encode(HmacSha256::digest(key, data))
    }

    #[test]
    fn test_empty_ctx() {
        let mut ctx = HmacSha256Ctx::default();
        let hmac = HmacSha256::new(&mut ctx, b"");
        let out = hmac.finalize();
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
        let mut ctx = HmacSha256Ctx::default();
        let mut hmac = HmacSha256::new(&mut ctx, key);
        for _ in 0..50 {
            hmac.update(b"\xdd");
        }
        let out = hmac.finalize();
        assert_eq!(
            hex::encode(out),
            "773ea91e36800e46854db8ebd09181a72959098b3ef8c122d9635514ced565fe"
        );

        // case 4
        let key = b"\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19";
        let mut ctx = HmacSha256Ctx::default();
        let mut hmac = HmacSha256::new(&mut ctx, key);
        for _ in 0..50 {
            hmac.update(b"\xcd");
        }
        let out = hmac.finalize();
        assert_eq!(
            hex::encode(out),
            "82558a389a443c0ea4cc819899f2083a85f0faa3e578f8077a2e3ff46729665b"
        );
    }

    #[test]
    fn test_guard_reuse() {
        let (key, data) = (b"Jefe", b"what do ya want for nothing?");
        let mut ctx = HmacSha256Ctx::default();
        for _ in 0..2 {
            let mut guard = HmacSha256Guard::hazard_new(&mut ctx);
            guard.init(key);
            guard.update(data);
            assert_eq!(hex::encode(guard.finalize()), hexdigest(key, data));
        }
    }

    const HMAC_SHA512_EMPTY: &str = "b936cee86c9f87aa5d3c6f2e84cb5a4239a5fe50480a6ec66b70ab5b1f4ac6730c6c515421b327ec1d69402e53dfb49ad7381eb067b338fd7b0cb22247225d47";
    // RFC 4231
    const HMAC_SHA512_VECTORS: &[(&[u8], &[u8], &str)] = &[
        (
            &[0x0b; 20],
            b"Hi There",
            "87aa7cdea5ef619d4ff0b4241a1d6cb02379f4e2ce4ec2787ad0b30545e17cdedaa833b7d6b8a702038b274eaea3f4e4be9d914eeb61f1702e696c203a126854",
        ),
        (
            b"Jefe",
            b"what do ya want for nothing?",
            "164b7a7bfcf819e2e395fbe73b56e0a387bd64222e831fd610270cd7ea2505549758bf75c05a994a6d034f65f8f0e6fdcaeab1a34d4a6b4b636e070a38bce737",
        ),
        (
            &[0xaa; 20],
            &[0xdd; 50],
            "fa73b0089d56a284efb0f0756c890be9b1b5dbdd8ee81a3655f83e33b2279d39bf3e848279a722c806b485a47e67c807b946a337bee8942674278859e13292fb",
        ),
        (
            &[0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f, 0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17, 0x18, 0x19],
            &[0xcd; 50],
            "b0ba465637458c6990e5a8c5f61d4af7e576d97ff94b872de76f8050361ee3dba91ca5c11aa25eb4d679275cc5788063a5f19741120c4f2de2adebeb10a298dd",
        ),
        // skipping case with truncation
        (
            &[0xaa; 131],
            b"Test Using Larger Than Block-Size Key - Hash Key First",
            "80b24263c7c1a3ebb71493c1dd7be8b49b46d1f41b4aeec1121b013783f8f3526b56d037e05f2598bd0fd2215d6a1e5295e64f73f63f0aec8b915a985d786598",
        ),
        (
            &[0xaa; 131],
            b"This is a test using a larger than block-size key and a larger than block-size data. The key needs to be hashed before being used by the HMAC algorithm.",
            "e37b6a775dc87dbaa4dfa9f96e5e3ffddebd71f8867289865df5a32d20cdc944b6022cac3c4982b10d5eeb55c3e4de15134676fb6de0446065c97440fa8c6a58",
        ),
        (
            b"",
            b"",
            HMAC_SHA512_EMPTY,
        ),
    ];

    fn hmac_512(key: &[u8], data: &[u8]) -> Digest512 {
        let mut ctx = HmacSha512Ctx::default();
        let mut guard = HmacSha512Guard::hazard_new(&mut ctx);
        guard.init(key);
        guard.update(data);
        guard.finalize()
    }

    #[test]
    fn test_empty_ctx_512() {
        assert_eq!(hex::encode(hmac_512(b"", b"")), HMAC_SHA512_EMPTY);
    }

    #[test]
    fn test_vectors_512() {
        for (key, data, expected) in HMAC_SHA512_VECTORS {
            assert_eq!(hex::encode(hmac_512(key, data)), *expected);
        }
    }

    #[test]
    fn test_update_512() {
        // RFC 4231 case 3, fed byte by byte
        let key = [0xaa; 20];
        let mut ctx = HmacSha512Ctx::default();
        let mut guard = HmacSha512Guard::hazard_new(&mut ctx);
        guard.init(&key);
        for _ in 0..50 {
            guard.update(&[0xdd]);
        }
        assert_eq!(hex::encode(guard.finalize()), HMAC_SHA512_VECTORS[2].2);
    }

    #[test]
    fn test_guard_reuse_512() {
        let (key, data) = (b"Jefe", b"what do ya want for nothing?");
        let mut ctx = HmacSha512Ctx::default();
        for _ in 0..2 {
            let mut guard = HmacSha512Guard::hazard_new(&mut ctx);
            guard.init(key);
            guard.update(data);
            assert_eq!(
                hex::encode(guard.finalize()),
                hex::encode(hmac_512(key, data))
            );
        }
    }
}

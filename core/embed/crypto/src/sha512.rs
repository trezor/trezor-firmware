use core::ops::DerefMut;

use rtl::CSlice;

use super::ffi;
use super::secret::{HazardGuard, SecretContext, SecretContextLock, ZeroableMemory};

pub const BLOCK_SIZE: usize = ffi::SHA512_BLOCK_LENGTH as usize;
pub const DIGEST_SIZE: usize = ffi::SHA512_DIGEST_LENGTH as usize;
pub type Digest = [u8; DIGEST_SIZE];

pub type Sha512Ctx = SecretContext<ffi::SHA512_CTX>;
pub type Sha512Guard<'a> = HazardGuard<'a, ffi::SHA512_CTX>;

// SAFETY: SHA512_CTX is valid when zeroed
unsafe impl ZeroableMemory for ffi::SHA512_CTX {}

impl ffi::SHA512_CTX {
    /// Initialize the SHA512 context.
    ///
    /// Called by [`Sha512::new`]. Call again when reusing the context after
    /// [`Self::hazard_finalize`] / [`HazardGuard::finalize`].
    ///
    /// # Copy hazard
    ///
    /// None because a "freshly initialized context" is public information.
    pub fn init(&mut self) {
        // SAFETY: ffi
        unsafe { ffi::sha512_Init(self) };
    }

    /// # Copy hazard
    ///
    /// The caller must not move or copy `self` for as long as it keeps
    /// using it via [`Self::hazard_update`] / [`Self::hazard_finalize`].
    /// Prefer [`Sha512`] which enforces this via pinning; this raw API only
    /// exists for callers that cannot use a pinned context (e.g. because
    /// they must own the hasher by value, as required by some external
    /// trait).
    pub fn hazard_update(&mut self, data: &[u8]) {
        let data_slice = CSlice::from(data);
        // SAFETY: ffi
        // COPY HAZARD: operates on the context in place
        unsafe { ffi::sha512_Update(self, data_slice.ptr(), data_slice.len()) };
    }

    /// # Copy hazard
    ///
    /// See [`Self::hazard_update`].
    pub fn hazard_finalize(&mut self) -> Digest {
        let mut digest = [0u8; DIGEST_SIZE];
        // SAFETY: ffi
        // COPY HAZARD: operates on the context in place
        unsafe { ffi::sha512_Final(self, digest.as_mut_ptr()) };
        digest
    }
}

impl Sha512Guard<'_> {
    /// Update the SHA512 context with the given data.
    pub fn update(&mut self, data: &[u8]) {
        // COPY HAZARD: implemented on a guard
        self.hazard_mut().hazard_update(data);
    }

    /// Finalize the SHA512 context and return the digest.
    ///
    /// After calling this method, the context is in a zeroized state. Before
    /// reusing it, the caller must call [`ffi::SHA512_CTX::init`] to
    /// reinitialize it.
    pub fn finalize(&mut self) -> Digest {
        // COPY HAZARD: implemented on a guard
        self.hazard_mut().hazard_finalize()
    }
}

pub struct Sha512<D: DerefMut<Target = Sha512Ctx>>(SecretContextLock<D>);

impl<D: DerefMut<Target = Sha512Ctx>> Sha512<D> {
    /// Construct a new SHA512 hasher.
    pub fn new(mut ctx: D) -> Self {
        // COPY HAZARD: init is a public operation
        ctx.hazard_mut().init();
        Self(SecretContextLock::new(ctx))
    }

    /// Update the SHA512 context with the given data.
    pub fn update(&mut self, data: &[u8]) {
        // COPY HAZARD: neither hazard call exfiltrates data
        self.0.guarded().update(data);
    }

    /// Finalize the SHA512 context and return the digest.
    pub fn finalize(&mut self) -> Digest {
        // COPY HAZARD: neither hazard call exfiltrates data
        self.0.guarded().finalize()
    }
}

pub fn digest_into(data: &[u8], out: &mut Digest) {
    let mut ctx = Sha512Ctx::default();
    let mut sha = Sha512::new(&mut ctx);
    sha.update(data);
    *out = sha.finalize();
}

pub fn digest(data: &[u8]) -> Digest {
    let mut out = [0u8; DIGEST_SIZE];
    digest_into(data, &mut out);
    out
}

#[cfg(test)]
mod test {
    use super::*;

    const SHA512_EMPTY: &str = "cf83e1357eefb8bdf1542850d66d8007d620e4050b5715dc83f4a921d36ce9ce47d0d13c5d85f2b0ff8318d2877eec2f63b931bd47417a81a538327af927da3e";
    const SHA512_VECTORS: &[(&[u8], &str)] = &[
        (b"", SHA512_EMPTY),
        (
            b"abc",
            "ddaf35a193617abacc417349ae20413112e6fa4e89a97ea20a9eeee64b55d39a2192992a274fc1a836ba3c23a3feebbd454d4423643ce80e2a9ac94fa54ca49f",
        ),
        (
            b"abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq",
            "204a8fc6dda82f0a0ced7beb8e08a41657c16ef468b228a8279be331a703c33596fd15c13b1b07f9aa1d3bea57789ca031ad85c7a71dd70354ec631238ca3445",
        ),
        (
            b"abcdefghbcdefghicdefghijdefghijkefghijklfghijklmghijklmnhijklmnoijklmnopjklmnopqklmnopqrlmnopqrsmnopqrstnopqrstu",
            "8e959b75dae313da8cf4f72814fc143f8f7779c6eb9f7fa17299aeadb6889018501d289e4900f7e4331b99dec4b5433ac7d329eeb6dd26545e96e55b874be909",
        ),
    ];

    fn hexdigest(data: &[u8]) -> String {
        hex::encode(digest(data))
    }

    #[test]
    fn test_empty_ctx() {
        let mut ctx = Sha512Ctx::default();
        let mut sha = Sha512::new(&mut ctx);
        let out_hex = hex::encode(sha.finalize());
        assert_eq!(out_hex, SHA512_EMPTY);
    }

    #[test]
    fn test_vectors() {
        for (data, expected) in SHA512_VECTORS {
            let out_hex = hexdigest(data);
            assert_eq!(out_hex, *expected);
        }
    }
}

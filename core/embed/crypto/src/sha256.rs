use core::ops::DerefMut;

use rtl::CSlice;

use super::ffi;
use super::secret::{HazardGuard, SecretContext, SecretContextLock, ZeroableMemory};

pub const BLOCK_SIZE: usize = ffi::SHA256_BLOCK_LENGTH as usize;
pub const DIGEST_SIZE: usize = ffi::SHA256_DIGEST_LENGTH as usize;
pub type Digest = [u8; DIGEST_SIZE];

pub type Sha256Ctx = SecretContext<ffi::SHA256_CTX>;

// SAFETY: SHA256_CTX is valid when zeroed
unsafe impl ZeroableMemory for ffi::SHA256_CTX {}

impl ffi::SHA256_CTX {
    /// Initialize the SHA256 context.
    ///
    /// Called by [`Sha256::new`]. Call again when reusing the context after
    /// [`HazardGuard::finalize`].
    pub fn init(&mut self) {
        // SAFETY: ffi
        unsafe { ffi::sha256_Init(self) };
    }
}

impl HazardGuard<'_, ffi::SHA256_CTX> {
    /// Update the SHA256 context with the given data.
    pub fn update(&mut self, data: &[u8]) {
        let ptr = CSlice::from(data);
        // SAFETY: ffi
        // COPY HAZARD: operates on the guarded context in place
        unsafe { ffi::sha256_Update(self.hazard_mut(), ptr.ptr(), ptr.len()) };
    }

    /// Finalize the SHA256 context and return the digest.
    ///
    /// After calling this method, the context is in a zeroized state. Before
    /// reusing it, the caller must call [`ffi::SHA256_CTX::init`] to
    /// reinitialize it.
    pub fn finalize(&mut self) -> Digest {
        let mut digest = [0u8; DIGEST_SIZE];
        // SAFETY: ffi
        // COPY HAZARD: operates on the guarded context in place
        unsafe { ffi::sha256_Final(self.hazard_mut(), digest.as_mut_ptr()) };
        digest
    }
}

/// SHA256 hasher.
///
/// A wrapper around a SHA256 context that provides a safe interface for hashing
/// data.
///
/// # Example
///
/// ```rust
/// use crypto::sha256::{Sha256, Sha256Ctx};
///
/// let mut ctx = Sha256Ctx::default();
/// let mut sha = Sha256::new(&mut ctx);
/// sha.update(b"hello");
/// sha.finalize();
/// ```
pub struct Sha256<D: DerefMut<Target = Sha256Ctx>>(SecretContextLock<D>);

impl<D: DerefMut<Target = Sha256Ctx>> Sha256<D> {
    /// Construct a new SHA256 hasher.
    pub fn new(mut ctx: D) -> Self {
        // COPY HAZARD: init is a public operation
        ctx.hazard_mut().init();
        Self(SecretContextLock::new(ctx))
    }

    /// Update the SHA256 context with the given data.
    pub fn update(&mut self, data: &[u8]) {
        self.0.guarded().update(data);
    }

    /// Finalize the SHA256 context and return the digest.
    pub fn finalize(mut self) -> Digest {
        self.0.guarded().finalize()
    }
}

impl Sha256<&'_ mut Sha256Ctx> {
    /// Calculate the SHA256 digest of the given data.
    pub fn digest(data: &[u8]) -> Digest {
        let mut ctx = SecretContext::default();
        let mut sha = Sha256::new(&mut ctx);
        sha.update(data);
        sha.finalize()
    }
}

#[cfg(test)]
mod test {
    use super::*;

    const SHA256_EMPTY: &str = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855";
    const SHA256_VECTORS: &[(&[u8], &str)] = &[
        (b"", SHA256_EMPTY),
        (
            b"abc",
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
        ),
    ];

    fn hexdigest(data: &[u8]) -> String {
        hex::encode(Sha256::digest(data))
    }

    #[test]
    fn test_empty_ctx() {
        let mut ctx = Sha256Ctx::default();
        let sha = Sha256::new(&mut ctx);
        let out = sha.finalize();

        let out_hex = hex::encode(out);
        assert_eq!(out_hex, SHA256_EMPTY.to_string());
    }

    #[test]
    fn test_vectors() {
        for (data, expected) in SHA256_VECTORS {
            let out_hex = hexdigest(data);
            assert_eq!(out_hex, *expected);
        }
    }
}

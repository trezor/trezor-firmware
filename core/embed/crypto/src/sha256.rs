use core::ops::DerefMut;
use core::pin::Pin;

use super::ffi;
use super::memory::Memory;
use crate::hasher::{PinnedHasher, RawHasher};
use crate::init_ctx;
use crate::memory::ZeroableMemory;

pub const BLOCK_SIZE: usize = ffi::SHA256_BLOCK_LENGTH as usize;
pub const DIGEST_SIZE: usize = ffi::SHA256_DIGEST_LENGTH as usize;
pub type Digest = [u8; DIGEST_SIZE];

pub type Sha256Ctx = ffi::SHA256_CTX;

// SAFETY: SHA256_CTX is valid when zeroed
unsafe impl ZeroableMemory for Sha256Ctx {}

impl Sha256Ctx {
    // SAFETY: this does not need to be unsafe because the constructed
    // context only has public data (the initial state)
    pub fn init_raw(&mut self) {
        // SAFETY: safe
        unsafe { ffi::sha256_Init(self) };
    }
}

impl RawHasher for Memory<Sha256Ctx> {
    type Digest = Digest;

    unsafe fn update_raw(&mut self, data: &[u8]) {
        unsafe { ffi::sha256_Update(self.as_mut(), data.as_ptr(), data.len()) };
    }

    unsafe fn finalize_raw(&mut self) -> Self::Digest {
        let mut digest = [0u8; DIGEST_SIZE];
        unsafe { ffi::sha256_Final(self.as_mut(), digest.as_mut_ptr()) };
        digest
    }
}

pub fn sha256_new<D>(mut ctx: Pin<D>) -> PinnedHasher<D>
where
    D: DerefMut<Target = Memory<Sha256Ctx>>,
{
    let mut mut_ctx = ctx.as_mut();
    unsafe {
        // SAFETY: init_raw does not invalidate the pin
        mut_ctx.inner().init_raw();
        // SAFETY: context is initialized
        PinnedHasher::new_no_init(ctx)
    }
}

pub fn digest(data: &[u8]) -> Digest {
    init_ctx!(ctx);
    let mut sha = sha256_new(ctx);
    sha.update(data);
    sha.finalize()
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
        hex::encode(digest(data))
    }

    #[test]
    fn test_empty_ctx() {
        init_ctx!(ctx);
        let mut sha = sha256_new(ctx);
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

use core::mem::MaybeUninit;
use core::ops::DerefMut;
use core::pin::Pin;

use super::ffi;
use super::memory::{Memory, init_ctx};
use crate::hasher::{PinnedHasher, RawHasher};
use crate::memory::ZeroableMemory;

pub const BLOCK_SIZE: usize = ffi::SHA256_BLOCK_LENGTH as usize;
pub const DIGEST_SIZE: usize = ffi::SHA256_DIGEST_LENGTH as usize;
pub type Digest = [u8; DIGEST_SIZE];

pub type Sha256Ctx = ffi::SHA256_CTX;

// SAFETY: SHA256_CTX is valid when zeroed
unsafe impl ZeroableMemory for Sha256Ctx {}

impl RawHasher for Sha256Ctx {
    type Digest = Digest;

    unsafe fn update(ctx: *mut Self, data: &[u8]) {
        unsafe { ffi::sha256_Update(ctx, data.as_ptr(), data.len()) };
    }

    unsafe fn finalize(ctx: *mut Self, output: &mut Self::Digest) {
        unsafe { ffi::sha256_Final(ctx, output.as_mut_ptr()) };
    }
}

pub type Sha256<'a> = PinnedHasher<&'a mut Memory<Sha256Ctx>>;

pub fn new_sha256<D: DerefMut<Target = Memory<Sha256Ctx>>>(ctx: Pin<D>) -> PinnedHasher<D> {
    let mut new = PinnedHasher::new_uninit(ctx);
    unsafe { ffi::sha256_Init(new.inner()) };
    new
}

pub fn digest_into(data: &[u8], out: &mut Digest) {
    init_ctx!(Sha256, ctx);
    ctx.update(data);
    ctx.finalize(out);
}

pub fn digest(data: &[u8]) -> Digest {
    let mut out = Digest::default();
    digest_into(data, &mut out);
    out
}

// Unpinned variant for use with noise-protocol which does not guarantee
// pinning. If possible please use [`Sha256`] above.
#[derive(Clone)]
pub struct NoPinSha256 {
    ctx: ffi::SHA256_CTX,
}

impl Drop for NoPinSha256 {
    fn drop(&mut self) {
        // C implementation zeroes the state
        // SAFETY: ffi
        unsafe { ffi::sha256_Final(&mut self.ctx as *mut _, core::ptr::null_mut()) };
    }
}

impl Default for NoPinSha256 {
    fn default() -> Self {
        let mut ctx = unsafe { MaybeUninit::<ffi::SHA256_CTX>::zeroed().assume_init() };
        unsafe { ffi::sha256_Init(&mut ctx) };
        Self { ctx }
    }
}

impl NoPinSha256 {
    pub fn update(&mut self, data: &[u8]) {
        // SAFETY: ffi
        unsafe { ffi::sha256_Update(&mut self.ctx as *mut _, data.as_ptr(), data.len()) };
    }

    pub fn finalize_into(mut self, out: &mut Digest) {
        // SAFETY: ffi
        unsafe { ffi::sha256_Final(&mut self.ctx as *mut _, out.as_mut_ptr()) };
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
        hex::encode(digest(data))
    }

    #[test]
    fn test_empty_ctx() {
        let mut out = Digest::default();

        init_ctx!(Sha256, ctx);
        ctx.finalize(&mut out);

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

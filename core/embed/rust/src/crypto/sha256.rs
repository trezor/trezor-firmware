use core::{mem::MaybeUninit, pin::Pin};

use zeroize::{DefaultIsZeroes, Zeroize as _};

use super::ffi;

type Memory = ffi::SHA256_CTX;

impl Default for Memory {
    fn default() -> Self {
        // SAFETY: a zeroed block of memory is a valid SHA256_CTX
        unsafe { MaybeUninit::<Memory>::zeroed().assume_init() }
    }
}

impl DefaultIsZeroes for Memory {}

pub const DIGEST_SIZE: usize = ffi::SHA256_DIGEST_LENGTH as usize;
pub type Digest = [u8; DIGEST_SIZE];

pub struct Sha256<'a> {
    ctx: Pin<&'a mut Memory>,
}

impl<'a> Sha256<'a> {
    pub fn new(mut ctx: Pin<&'a mut Memory>) -> Self {
        // initialize the context
        // SAFETY: safe with whatever finds itself as memory contents
        unsafe { ffi::sha256_Init(ctx.as_mut().get_unchecked_mut()) };
        Self { ctx }
    }

    pub fn update(&mut self, data: &[u8]) {
        // SAFETY: safe
        unsafe {
            ffi::sha256_Update(
                self.ctx.as_mut().get_unchecked_mut(),
                data.as_ptr(),
                data.len(),
            )
        };
    }

    pub fn memory() -> Memory {
        Memory::default()
    }

    pub fn finalize_into(mut self, out: &mut Digest) {
        // SAFETY: safe
        unsafe { ffi::sha256_Final(self.ctx.as_mut().get_unchecked_mut(), out.as_mut_ptr()) };
    }
}

impl Drop for Sha256<'_> {
    fn drop(&mut self) {
        self.ctx.zeroize();
    }
}

macro_rules! init_ctx {
    ($name:ident) => {
        // assign the backing memory to $name...
        let mut $name = crate::crypto::sha256::Sha256::memory();
        // ... then make it inaccessible by overwriting the binding, and pin it
        #[allow(unused_mut)]
        let mut $name = unsafe {
            crate::crypto::sha256::Sha256::new(core::pin::Pin::new_unchecked(&mut $name))
        };
    };
}

pub(crate) use init_ctx;

pub fn digest_into(data: &[u8], out: &mut Digest) {
    init_ctx!(ctx);
    ctx.update(data);
    ctx.finalize_into(out);
}

pub fn digest(data: &[u8]) -> Digest {
    let mut out = Digest::default();
    digest_into(data, &mut out);
    out
}

#[cfg(test)]
mod test {
    use crate::strutil::hexlify;

    use super::*;

    const SHA256_EMPTY: &[u8] = b"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855";
    const SHA256_VECTORS: &[(&[u8], &[u8])] = &[
        (b"", SHA256_EMPTY),
        (
            b"abc",
            b"ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
        ),
    ];

    fn hexdigest(data: &[u8]) -> [u8; DIGEST_SIZE * 2] {
        let mut out_hex = [0u8; DIGEST_SIZE * 2];

        let digest = digest(data);
        hexlify(&digest, &mut out_hex);
        out_hex
    }

    #[test]
    fn test_empty_ctx() {
        let mut out = Digest::default();
        let mut out_hex = [0u8; DIGEST_SIZE * 2];

        init_ctx!(ctx);
        ctx.finalize_into(&mut out);
        hexlify(&out, &mut out_hex);

        assert_eq!(out_hex, SHA256_EMPTY);
    }

    #[test]
    fn test_vectors() {
        for (data, expected) in SHA256_VECTORS {
            let out_hex = hexdigest(data);
            assert_eq!(out_hex, *expected);
        }
    }
}

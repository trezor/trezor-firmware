use core::{mem::MaybeUninit, pin::Pin};

use zeroize::{DefaultIsZeroes, Zeroize as _};

use super::ffi;

type Memory = ffi::SHA512_CTX;

impl Default for Memory {
    fn default() -> Self {
        // SAFETY: a zeroed block of memory is a valid SHA512_CTX
        unsafe { MaybeUninit::<Memory>::zeroed().assume_init() }
    }
}

impl DefaultIsZeroes for Memory {}

pub const DIGEST_SIZE: usize = ffi::SHA512_DIGEST_LENGTH as usize;
pub type Digest = [u8; DIGEST_SIZE];

pub struct Sha512<'a> {
    ctx: Pin<&'a mut Memory>,
}

impl<'a> Sha512<'a> {
    pub fn new(mut ctx: Pin<&'a mut Memory>) -> Self {
        // initialize the context
        // SAFETY: safe with whatever finds itself as memory contents
        unsafe { ffi::sha512_Init(ctx.as_mut().get_unchecked_mut()) };
        Self { ctx }
    }

    pub fn update(&mut self, data: &[u8]) {
        // SAFETY: ffi
        unsafe {
            ffi::sha512_Update(
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
        // SAFETY: ffi
        unsafe { ffi::sha512_Final(self.ctx.as_mut().get_unchecked_mut(), out.as_mut_ptr()) };
    }
}

impl Drop for Sha512<'_> {
    fn drop(&mut self) {
        self.ctx.zeroize();
    }
}

macro_rules! init_ctx {
    ($name:ident) => {
        // assign the backing memory to $name...
        let mut $name = crate::crypto::sha512::Sha512::memory();
        // ... then make it inaccessible by overwriting the binding, and pin it
        #[allow(unused_mut)]
        let mut $name = crate::crypto::sha512::Sha512::new(core::pin::Pin::new(&mut $name));
    };
}

pub(crate) use init_ctx;

pub fn digest_into(data: &[u8], out: &mut Digest) {
    init_ctx!(ctx);
    ctx.update(data);
    ctx.finalize_into(out);
}

pub fn digest(data: &[u8]) -> Digest {
    let mut out = [0u8; DIGEST_SIZE];
    digest_into(data, &mut out);
    out
}

#[cfg(test)]
mod test {
    use crate::strutil::hexlify;

    use super::*;

    const SHA512_EMPTY: &[u8] = b"cf83e1357eefb8bdf1542850d66d8007d620e4050b5715dc83f4a921d36ce9ce47d0d13c5d85f2b0ff8318d2877eec2f63b931bd47417a81a538327af927da3e";
    const SHA512_VECTORS: &[(&[u8], &[u8])] = &[
        (b"", SHA512_EMPTY),
        (
            b"abc",
            b"ddaf35a193617abacc417349ae20413112e6fa4e89a97ea20a9eeee64b55d39a2192992a274fc1a836ba3c23a3feebbd454d4423643ce80e2a9ac94fa54ca49f",
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
        let mut out = [0u8; DIGEST_SIZE];
        let mut out_hex = [0u8; DIGEST_SIZE * 2];

        init_ctx!(ctx);
        ctx.finalize_into(&mut out);
        hexlify(&out, &mut out_hex);

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

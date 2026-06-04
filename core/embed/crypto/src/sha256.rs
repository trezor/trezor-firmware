use core::pin::Pin;

use zeroize::Zeroize as _;

use super::{
    ffi,
    memory::{Memory, init_ctx},
};

pub const DIGEST_SIZE: usize = ffi::SHA256_DIGEST_LENGTH as usize;
pub type Digest = [u8; DIGEST_SIZE];

pub struct Sha256<'a> {
    ctx: Pin<&'a mut Memory<ffi::SHA256_CTX>>,
}

impl<'a> Sha256<'a> {
    pub fn new(mut ctx: Pin<&'a mut Memory<ffi::SHA256_CTX>>) -> Self {
        // initialize the context
        // SAFETY: safe with whatever finds itself as memory contents
        unsafe { ffi::sha256_Init(ctx.inner()) };
        Self { ctx }
    }

    pub fn update(&mut self, data: &[u8]) {
        // SAFETY: safe
        unsafe { ffi::sha256_Update(self.ctx.inner(), data.as_ptr(), data.len()) };
    }

    pub fn memory() -> Memory<ffi::SHA256_CTX> {
        Memory::default()
    }

    pub fn finalize_into(mut self, out: &mut Digest) {
        // SAFETY: safe
        unsafe { ffi::sha256_Final(self.ctx.inner(), out.as_mut_ptr()) };
    }
}

impl Drop for Sha256<'_> {
    fn drop(&mut self) {
        self.ctx.zeroize();
    }
}

pub fn digest_into(data: &[u8], out: &mut Digest) {
    init_ctx!(Sha256, ctx);
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
        let digest = digest(data);
        hex::encode(digest)
    }

    #[test]
    fn test_empty_ctx() {
        let mut out = Digest::default();

        init_ctx!(Sha256, ctx);
        ctx.finalize_into(&mut out);
        let out_hex = hex::encode(out);

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

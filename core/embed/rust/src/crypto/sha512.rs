use core::pin::Pin;

use super::{ffi, memory::Memory};

use zeroize::Zeroize as _;

pub const DIGEST_SIZE: usize = ffi::SHA512_DIGEST_LENGTH as usize;
pub type Digest = [u8; DIGEST_SIZE];

pub struct Sha512<'a> {
    ctx: Pin<&'a mut Memory<ffi::SHA512_CTX>>,
}

impl<'a> Sha512<'a> {
    pub fn new(ctx: Pin<&'a mut Memory<ffi::SHA512_CTX>>) -> Self {
        // initialize the context
        let mut res = Self { ctx };
        // SAFETY: safe with whatever finds itself as memory contents
        unsafe { ffi::sha512_Init(res.ctx.inner()) };
        res
    }

    pub fn update(&mut self, data: &[u8]) {
        // SAFETY: ffi
        unsafe { ffi::sha512_Update(self.ctx.inner(), data.as_ptr(), data.len()) };
    }

    pub fn memory() -> Memory<ffi::SHA512_CTX> {
        Memory::default()
    }

    pub fn finalize_into(mut self, out: &mut Digest) {
        // SAFETY: ffi
        unsafe { ffi::sha512_Final(self.ctx.inner(), out.as_mut_ptr()) };
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
        let mut $name = unsafe {
            crate::crypto::sha512::Sha512::new(core::pin::Pin::new_unchecked(&mut $name))
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
        (
            b"abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq",
            b"204a8fc6dda82f0a0ced7beb8e08a41657c16ef468b228a8279be331a703c33596fd15c13b1b07f9aa1d3bea57789ca031ad85c7a71dd70354ec631238ca3445",
        ),
        (
            b"abcdefghbcdefghicdefghijdefghijkefghijklfghijklmghijklmnhijklmnoijklmnopjklmnopqklmnopqrlmnopqrsmnopqrstnopqrstu",
            b"8e959b75dae313da8cf4f72814fc143f8f7779c6eb9f7fa17299aeadb6889018501d289e4900f7e4331b99dec4b5433ac7d329eeb6dd26545e96e55b874be909",
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

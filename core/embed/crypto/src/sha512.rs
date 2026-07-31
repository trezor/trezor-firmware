use core::ops::DerefMut;
use core::pin::Pin;

use super::ffi;
use super::memory::Memory;
use crate::hasher::{PinnedHasher, RawHasher};
use crate::init_ctx;
use crate::memory::ZeroableMemory;

pub const BLOCK_SIZE: usize = ffi::SHA512_BLOCK_LENGTH as usize;
pub const DIGEST_SIZE: usize = ffi::SHA512_DIGEST_LENGTH as usize;
pub type Digest = [u8; DIGEST_SIZE];

pub type Sha512Ctx = ffi::SHA512_CTX;

unsafe impl ZeroableMemory for Sha512Ctx {}

impl Sha512Ctx {
    // SAFETY:
    // init_raw is safe because it doesn't encode any sensitive data
    // into the context
    pub fn init_raw(&mut self) {
        unsafe { ffi::sha512_Init(self) };
    }
}

impl RawHasher for Memory<Sha512Ctx> {
    type Digest = Digest;

    unsafe fn update_raw(&mut self, data: &[u8]) {
        unsafe { ffi::sha512_Update(self.as_mut(), data.as_ptr(), data.len()) };
    }

    unsafe fn finalize_raw(&mut self) -> Self::Digest {
        let mut digest = [0u8; DIGEST_SIZE];
        unsafe { ffi::sha512_Final(self.as_mut(), digest.as_mut_ptr()) };
        digest
    }
}

pub fn sha512_new<D>(mut ctx: Pin<D>) -> PinnedHasher<D>
where
    D: DerefMut<Target = Memory<Sha512Ctx>>,
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
    let mut sha = sha512_new(ctx);
    sha.update(data);
    sha.finalize()
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
        init_ctx!(ctx);
        let mut sha = sha512_new(ctx);
        let out = sha.finalize();

        let out_hex = hex::encode(out);
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

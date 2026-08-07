use core::ops::DerefMut;
use core::pin::Pin;

use rtl::util::FatPtr;

use crate::hasher::{PinnedHasher, RawHasher};
use crate::memory::{Memory, ZeroableMemory};
use crate::{ffi, init_ctx};

pub enum Sha3BitSize {
    Sha3_224 = 224,
    Sha3_256 = 256,
    Sha3_384 = 384,
    Sha3_512 = 512,
}

pub struct Sha3Ctx<const BIT_SIZE: usize> {
    ctx: ffi::SHA3_CTX,
    is_keccak: bool,
}

fn sha3_init_raw(ctx: &mut ffi::SHA3_CTX, bit_size: u32) {
    // SAFETY: ffi
    unsafe { ffi::keccak_Init(ctx, bit_size) };
}

fn sha3_update_raw(ctx: &mut ffi::SHA3_CTX, data: &[u8]) {
    let ptr = FatPtr::from(data);
    // SAFETY: ffi
    unsafe { ffi::sha3_Update(ctx, ptr.ptr(), ptr.len()) };
}

fn sha3_final_raw(ctx: &mut ffi::SHA3_CTX, buffer: &mut [u8]) {
    // SAFETY: ffi
    unsafe { ffi::sha3_Final(ctx, buffer.as_mut_ptr()) };
}

fn keccak_final_raw(ctx: &mut ffi::SHA3_CTX, buffer: &mut [u8]) {
    // SAFETY: ffi
    unsafe { ffi::keccak_Final(ctx, buffer.as_mut_ptr()) };
}

unsafe impl<const BIT_SIZE: usize> ZeroableMemory for Sha3Ctx<BIT_SIZE> {}

impl<const BIT_SIZE: usize> Sha3Ctx<BIT_SIZE> {
    // SAFETY:
    // init_raw is safe because it doesn't encode any sensitive data
    // into the context
    pub fn init_raw(&mut self, is_keccak: bool) {
        sha3_init_raw(&mut self.ctx, BIT_SIZE as u32);
        self.is_keccak = is_keccak;
    }
}

/// Empty SHA3 struct carrying the helper functions:
///
/// Sha3::<256>::new_pinned(ctx) creates a PinnedHasher
/// Sha3::<224>::digest(data) calculates and returns the digest
pub struct Sha3<const BIT_SIZE: usize>(core::marker::PhantomData<[u8; BIT_SIZE]>);

/// Empty Keccak struct carrying the helper functions:
///
/// Keccak::<256>::new_pinned(ctx) creates a PinnedHasher
/// Keccak::<224>::digest(data) calculates and returns the digest
pub struct Keccak<const BIT_SIZE: usize>(core::marker::PhantomData<[u8; BIT_SIZE]>);

macro_rules! impl_raw_hasher {
    ($bit_size:literal, $digest_size:expr) => {
        impl Sha3<$bit_size> {
            pub fn new_pinned<D>(mut ctx: Pin<D>) -> PinnedHasher<D>
            where
                D: DerefMut<Target = Memory<Sha3Ctx<$bit_size>>>,
            {
                let mut mut_ctx = ctx.as_mut();

                unsafe {
                    // SAFETY: init_raw does not invalidate the pin
                    mut_ctx.inner().init_raw(false);
                    // SAFETY: context is initialized
                    PinnedHasher::new_no_init(ctx)
                }
            }

            pub fn digest(data: &[u8]) -> <Memory<Sha3Ctx<$bit_size>> as RawHasher>::Digest {
                init_ctx!(ctx);
                let mut sha = Self::new_pinned(ctx);
                sha.update(data);
                sha.finalize()
            }
        }

        impl Keccak<$bit_size> {
            pub fn new_pinned<D>(mut ctx: Pin<D>) -> PinnedHasher<D>
            where
                D: DerefMut<Target = Memory<Sha3Ctx<$bit_size>>>,
            {
                let mut mut_ctx = ctx.as_mut();
                unsafe {
                    // SAFETY: init_raw does not invalidate the pin
                    mut_ctx.inner().init_raw(true);
                    // SAFETY: context is initialized
                    PinnedHasher::new_no_init(ctx)
                }
            }

            pub fn digest(data: &[u8]) -> <Memory<Sha3Ctx<$bit_size>> as RawHasher>::Digest {
                init_ctx!(ctx);
                let mut sha = Self::new_pinned(ctx);
                sha.update(data);
                sha.finalize()
            }
        }

        impl RawHasher for Memory<Sha3Ctx<$bit_size>> {
            type Digest = [u8; $digest_size];

            unsafe fn update_raw(&mut self, data: &[u8]) {
                sha3_update_raw(&mut self.ctx, data);
            }

            unsafe fn finalize_raw(&mut self) -> Self::Digest {
                let mut digest = [0u8; $digest_size];
                if self.is_keccak {
                    keccak_final_raw(&mut self.ctx, &mut digest);
                } else {
                    sha3_final_raw(&mut self.ctx, &mut digest);
                }
                digest
            }
        }
    };
}

impl_raw_hasher!(224, ffi::SHA3_224_DIGEST_LENGTH as usize);
impl_raw_hasher!(256, ffi::SHA3_256_DIGEST_LENGTH as usize);
impl_raw_hasher!(384, ffi::SHA3_384_DIGEST_LENGTH as usize);
impl_raw_hasher!(512, ffi::SHA3_512_DIGEST_LENGTH as usize);

#[cfg(test)]
mod test {
    use super::*;

    // vectors from https://www.di-mgt.com.au/sha_testvectors.html
    const SHA3_256_EMPTY: &str = "a7ffc6f8bf1ed76651c14756a061d662f580ff4de43b49fa82d80a4b80f8434a";
    const SHA3_256_VECTORS: &[(&[u8], &str)] = &[
        (b"", SHA3_256_EMPTY),
        (
            b"abc",
            "3a985da74fe225b2045c172d6bd390bd855f086e3e9d525b46bfe24511431532",
        ),
        (
            b"abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq",
            "41c0dba2a9d6240849100376a8235e2c82e1b9998a999e21db32dd97496d3376",
        ),
        (
            b"abcdefghbcdefghicdefghijdefghijkefghijklfghijklmghijklmnhijklmnoijklmnopjklmnopqklmnopqrlmnopqrsmnopqrstnopqrstu",
            "916f6061fe879741ca6469b43971dfdb28b1a32dc36cb3254e812be27aad1d18",
        ),
    ];

    const KECCAK_256_EMPTY: &str =
        "c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470";
    const KECCAK_256_VECTORS: &[(&[u8], &str)] = &[
        (b"", KECCAK_256_EMPTY),
        (
            b"abc",
            "4e03657aea45a94fc7d47ba826c8d667c0d1e6e33a64a036ec44f58fa12d6c45",
        ),
        (
            b"abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq",
            "45d3b367a6904e6e8d502ee04999a7c27647f91fa845d456525fd352ae3d7371",
        ),
        (
            b"abcdefghbcdefghicdefghijdefghijkefghijklfghijklmghijklmnhijklmnoijklmnopjklmnopqklmnopqrlmnopqrsmnopqrstnopqrstu",
            "f519747ed599024f3882238e5ab43960132572b7345fbeb9a90769dafd21ad67",
        ),
    ];

    const SHA3_512_EMPTY: &str = "a69f73cca23a9ac5c8b567dc185a756e97c982164fe25859e0d1dcc1475c80a615b2123af1f5f94c11e3e9402c3ac558f500199d95b6d3e301758586281dcd26";
    const SHA3_512_VECTORS: &[(&[u8], &str)] = &[
        (b"", SHA3_512_EMPTY),
        (
            b"abc",
            "b751850b1a57168a5693cd924b6b096e08f621827444f70d884f5d0240d2712e10e116e9192af3c91a7ec57647e3934057340b4cf408d5a56592f8274eec53f0",
        ),
        (
            b"abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq",
            "04a371e84ecfb5b8b77cb48610fca8182dd457ce6f326a0fd3d7ec2f1e91636dee691fbe0c985302ba1b0d8dc78c086346b533b49c030d99a27daf1139d6e75e",
        ),
        (
            b"abcdefghbcdefghicdefghijdefghijkefghijklfghijklmghijklmnhijklmnoijklmnopjklmnopqklmnopqrlmnopqrsmnopqrstnopqrstu",
            "afebb2ef542e6579c50cad06d2e578f9f8dd6881d7dc824d26360feebf18a4fa73e3261122948efcfd492e74e82e2189ed0fb440d187f382270cb455f21dd185",
        ),
    ];

    const KECCAK_512_EMPTY: &str = "0eab42de4c3ceb9235fc91acffe746b29c29a8c366b7c60e4e67c466f36a4304c00fa9caf9d87976ba469bcbe06713b435f091ef2769fb160cdab33d3670680e";
    const KECCAK_512_VECTORS: &[(&[u8], &str)] = &[
        (b"", KECCAK_512_EMPTY),
        (
            b"abc",
            "18587dc2ea106b9a1563e32b3312421ca164c7f1f07bc922a9c83d77cea3a1e5d0c69910739025372dc14ac9642629379540c17e2a65b19d77aa511a9d00bb96",
        ),
        (
            b"abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq",
            "6aa6d3669597df6d5a007b00d09c20795b5c4218234e1698a944757a488ecdc09965435d97ca32c3cfed7201ff30e070cd947f1fc12b9d9214c467d342bcba5d",
        ),
        (
            b"abcdefghbcdefghicdefghijdefghijkefghijklfghijklmghijklmnhijklmnoijklmnopjklmnopqklmnopqrlmnopqrsmnopqrstnopqrstu",
            "ac2fb35251825d3aa48468a9948c0a91b8256f6d97d8fa4160faff2dd9dfcc24f3f1db7a983dad13d53439ccac0b37e24037e7b95f80f59f37a2f683c4ba4682",
        ),
    ];

    #[test]
    fn test_empty_ctx_sha3_256() {
        init_ctx!(ctx);
        let mut sha = Sha3::<256>::new_pinned(ctx);
        assert_eq!(hex::encode(sha.finalize()), SHA3_256_EMPTY);
    }

    #[test]
    fn test_empty_ctx_keccak_256() {
        init_ctx!(ctx);
        let mut sha = Keccak::<256>::new_pinned(ctx);
        assert_eq!(hex::encode(sha.finalize()), KECCAK_256_EMPTY);
    }

    #[test]
    fn test_sha3_256_vectors() {
        for (data, expected) in SHA3_256_VECTORS {
            assert_eq!(hex::encode(Sha3::<256>::digest(data)), *expected);
        }
    }

    #[test]
    fn test_keccak_256_vectors() {
        for (data, expected) in KECCAK_256_VECTORS {
            assert_eq!(hex::encode(Keccak::<256>::digest(data)), *expected);
        }
    }

    #[test]
    fn test_sha3_512_vectors() {
        for (data, expected) in SHA3_512_VECTORS {
            assert_eq!(hex::encode(Sha3::<512>::digest(data)), *expected);
        }
    }

    #[test]
    fn test_keccak_512_vectors() {
        for (data, expected) in KECCAK_512_VECTORS {
            assert_eq!(hex::encode(Keccak::<512>::digest(data)), *expected);
        }
    }
}

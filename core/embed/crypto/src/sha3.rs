use core::ops::DerefMut;

use rtl::CSlice;
use rtl::error::ensure;

use super::secret::{HazardGuard, SecretContext, SecretContextLock, ZeroableMemory};
use super::{Error, ffi};

pub type Sha3Ctx = SecretContext<ffi::SHA3_CTX>;

impl ffi::SHA3_CTX {
    /// Initialize the SHA3/Keccak context for the given digest bit size.
    ///
    /// # Copy hazard
    ///
    /// None because a "freshly initialized context" is public information.
    fn init(&mut self, bit_size: u32) -> Result<(), Error> {
        // SAFETY: ffi
        // COPY HAZARD: no sensitive data is encoded into the state
        if unsafe { ffi::keccak_Init(self, bit_size) } {
            Ok(())
        } else {
            Err(Error::InvalidParams)
        }
    }
}

impl HazardGuard<'_, ffi::SHA3_CTX> {
    /// Update the SHA3/Keccak context with the given data.
    fn update(&mut self, data: &[u8]) {
        let ptr = CSlice::from(data);
        // SAFETY: ffi
        // COPY HAZARD: operates on the guarded context in place
        unsafe { ffi::sha3_Update(self.hazard_mut(), ptr.ptr(), ptr.len()) };
    }

    /// Finalize as SHA-3 into `buffer`.
    fn sha3_finalize(&mut self, buffer: &mut [u8]) {
        // SAFETY: ffi
        // COPY HAZARD: operates on the guarded context in place
        unsafe { ffi::sha3_Final(self.hazard_mut(), buffer.as_mut_ptr()) };
    }

    /// Finalize as Keccak into `buffer`.
    fn keccak_finalize(&mut self, buffer: &mut [u8]) {
        // SAFETY: ffi
        // COPY HAZARD: operates on the guarded context in place
        unsafe { ffi::keccak_Final(self.hazard_mut(), buffer.as_mut_ptr()) };
    }
}

// SAFETY: SHA3_CTX is valid when zeroed
unsafe impl ZeroableMemory for ffi::SHA3_CTX {}

macro_rules! impl_raw_hasher {
    ($name:ident, $bit_size:literal, $is_keccak:literal, $digest_size:expr) => {
        /// SHA-3 / Keccak hasher.
        pub struct $name<D: DerefMut<Target = Sha3Ctx>>(SecretContextLock<D>);

        impl<D: DerefMut<Target = Sha3Ctx>> $name<D> {
            #[doc = concat!("Construct a new `", stringify!($name), "` hasher.")]
            pub fn new(mut ctx: D) -> Self {
                // COPY HAZARD: init is a public operation
                ensure!(ctx.hazard_mut().init($bit_size).is_ok(), "Invalid SHA3 bit size");
                Self(SecretContextLock::new(ctx))
            }

            #[doc = concat!("Update the `", stringify!($name), "` context with the given data.")]
            pub fn update(&mut self, data: &[u8]) {
                self.0.guarded().update(data);
            }

            #[doc = concat!("Finalize the `", stringify!($name), "` context and return the digest.")]
            pub fn finalize(mut self) -> [u8; $digest_size] {
                let mut buffer = [0u8; $digest_size];
                if $is_keccak {
                    self.0.guarded().keccak_finalize(&mut buffer);
                } else {
                    self.0.guarded().sha3_finalize(&mut buffer);
                }
                buffer
            }
        }

        impl $name<&'_ mut Sha3Ctx> {
            #[doc = concat!("Calculate the `", stringify!($name), "` digest of the given data.")]
            pub fn digest(data: &[u8]) -> [u8; $digest_size] {
                let mut ctx = Sha3Ctx::default();
                let mut sha = $name::new(&mut ctx);
                sha.update(data);
                sha.finalize()
            }
        }
    };
}

impl_raw_hasher!(Sha3_224, 224, false, ffi::SHA3_224_DIGEST_LENGTH as usize);
impl_raw_hasher!(Sha3_256, 256, false, ffi::SHA3_256_DIGEST_LENGTH as usize);
impl_raw_hasher!(Sha3_384, 384, false, ffi::SHA3_384_DIGEST_LENGTH as usize);
impl_raw_hasher!(Sha3_512, 512, false, ffi::SHA3_512_DIGEST_LENGTH as usize);
impl_raw_hasher!(Keccak224, 224, true, ffi::SHA3_224_DIGEST_LENGTH as usize);
impl_raw_hasher!(Keccak256, 256, true, ffi::SHA3_256_DIGEST_LENGTH as usize);
impl_raw_hasher!(Keccak384, 384, true, ffi::SHA3_384_DIGEST_LENGTH as usize);
impl_raw_hasher!(Keccak512, 512, true, ffi::SHA3_512_DIGEST_LENGTH as usize);

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
        let mut ctx = Sha3Ctx::default();
        let sha = Sha3_256::new(&mut ctx);
        assert_eq!(hex::encode(sha.finalize()), SHA3_256_EMPTY);
    }

    #[test]
    fn test_empty_ctx_keccak_256() {
        let mut ctx = Sha3Ctx::default();
        let sha = Keccak256::new(&mut ctx);
        assert_eq!(hex::encode(sha.finalize()), KECCAK_256_EMPTY);
    }

    #[test]
    fn test_sha3_256_vectors() {
        for (data, expected) in SHA3_256_VECTORS {
            assert_eq!(hex::encode(Sha3_256::digest(data)), *expected);
        }
    }

    #[test]
    fn test_keccak_256_vectors() {
        for (data, expected) in KECCAK_256_VECTORS {
            assert_eq!(hex::encode(Keccak256::digest(data)), *expected);
        }
    }

    #[test]
    fn test_sha3_512_vectors() {
        for (data, expected) in SHA3_512_VECTORS {
            assert_eq!(hex::encode(Sha3_512::digest(data)), *expected);
        }
    }

    #[test]
    fn test_keccak_512_vectors() {
        for (data, expected) in KECCAK_512_VECTORS {
            assert_eq!(hex::encode(Keccak512::digest(data)), *expected);
        }
    }
}

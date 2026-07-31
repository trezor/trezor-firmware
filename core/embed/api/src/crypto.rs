use stabby::boxed::BoxedSlice;
use stabby::boxed::Box;
use stabby::slice::Slice;
use stabby::str::Str;
use stabby::string::String;
use trezor_app_sdk::traits::crypto::{
    BoxedHasher, CryptoError, CryptoV1, DerivationPath, EcCurve, HashingAlgorithm, Xpub,
};
use trezor_app_sdk::traits::util::FastResult;

pub struct TrezorCryptoV1Impl;

impl CryptoV1 for TrezorCryptoV1Impl {
    extern "C" fn get_hasher(&self, algorithm: HashingAlgorithm) -> BoxedHasher {
        match algorithm {
            HashingAlgorithm::Sha256 => BoxedHasher::Sha256(sha256::Sha256::new()),
            HashingAlgorithm::Sha512 => BoxedHasher::Sha512(sha512::Sha512::new()),
            HashingAlgorithm::Sha3_256 => BoxedHasher::Sha3_256(sha3::Sha3_256::new()),
            HashingAlgorithm::Sha3_512 => BoxedHasher::Sha3_512(sha3::Sha3_512::new()),
        }
    }

    extern "C" fn ec_verify_recover<'a>(
        &self,
        curve: EcCurve,
        public_key: Slice<'a, u8>,
        signature: Slice<'a, u8>,
        message: Slice<'a, u8>,
    ) -> FastResult<BoxedSlice<u8>, CryptoError> {
        todo!()
    }

    extern "C" fn ec_verify_recover_digest<'a>(
        &self,
        curve: EcCurve,
        public_key: Slice<'a, u8>,
        signature: Slice<'a, u8>,
        digest: Slice<'a, u8>,
    ) -> FastResult<BoxedSlice<u8>, CryptoError> {
        todo!()
    }

    extern "C" fn ec_sign<'a>(
        &self,
        curve: EcCurve,
        derivation_path: DerivationPath<'a>,
        message: Slice<'a, u8>,
    ) -> FastResult<BoxedSlice<u8>, CryptoError> {
        todo!()
    }

    extern "C" fn ec_sign_digest<'a>(
        &self,
        curve: EcCurve,
        derivation_path: DerivationPath<'a>,
        digest: Slice<'a, u8>,
    ) -> FastResult<BoxedSlice<u8>, CryptoError> {
        todo!()
    }

    extern "C" fn get_xpub<'a>(
        &self,
        curve: EcCurve,
        derivation_path: DerivationPath<'a>,
    ) -> FastResult<Xpub, CryptoError> {
        todo!()
    }

    extern "C" fn base58_encode<'a>(&self, data: Slice<'a, u8>) -> String {
        todo!()
    }

    extern "C" fn base58_decode<'a>(
        &self,
        data: Str<'a>,
    ) -> FastResult<BoxedSlice<u8>, CryptoError> {
        todo!()
    }

    extern "C" fn base58check_encode<'a>(&self, data: Slice<'a, u8>) -> String {
        todo!()
    }

    extern "C" fn base58check_decode<'a>(
        &self,
        data: Str<'a>,
    ) -> FastResult<BoxedSlice<u8>, CryptoError> {
        todo!()
    }
}

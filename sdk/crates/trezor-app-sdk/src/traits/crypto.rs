use stabby::alloc::string::String;
use stabby::boxed::{Box, BoxedSlice};
use stabby::slice::Slice;
use stabby::str::Str;

use super::util::FastResult;

#[stabby::stabby]
#[repr(u8)]
pub enum CryptoError {
    InvalidPublicKey,
    InvalidSignature,
    InvalidEncoding,
}

#[stabby::stabby(checked)]
pub trait Hasher {
    extern "C" fn update<'a>(&mut self, input: Slice<'a, u8>);
    extern "C" fn finalize(&mut self) -> BoxedSlice<u8>;
}

pub type BoxedHasher = stabby::dynptr!(Box<dyn Hasher>);

#[stabby::stabby]
#[repr(u8)]
pub enum HashingAlgorithm {
    Sha256,
    Sha3_256,
    Sha512,
    Keccak256,
    HmacSha256,
}

#[stabby::stabby]
#[repr(u8)]
pub enum EcCurve {
    Secp256k1,
    Nist256p1,
    Ed25519,
}

#[stabby::stabby]
pub struct Xpub {
    pub version: [u8; 4],
    pub depth: u8,
    pub fingerprint: [u8; 4],
    pub child_number_bytes: [u8; 4],
    pub chain_code: [u8; 32],
    pub key: [u8; 33],
}

impl Xpub {
    pub fn child_number(&self) -> u32 {
        u32::from_be_bytes(self.child_number_bytes)
    }
}

pub type DerivationPath<'a> = Slice<'a, u32>;

#[stabby::stabby(checked)]
pub trait CryptoV1: Send + Sync {
    extern "C" fn get_hasher(&self, algorithm: HashingAlgorithm) -> BoxedHasher;
    extern "C" fn ec_verify_recover<'a>(
        &self,
        curve: EcCurve,
        public_key: Slice<'a, u8>,
        signature: Slice<'a, u8>,
        message: Slice<'a, u8>,
    ) -> FastResult<BoxedSlice<u8>, CryptoError>;
    extern "C" fn ec_verify_recover_digest<'a>(
        &self,
        curve: EcCurve,
        public_key: Slice<'a, u8>,
        signature: Slice<'a, u8>,
        digest: Slice<'a, u8>,
    ) -> FastResult<BoxedSlice<u8>, CryptoError>;

    extern "C" fn ec_sign<'a>(
        &self,
        curve: EcCurve,
        derivation_path: DerivationPath<'a>,
        message: Slice<'a, u8>,
    ) -> FastResult<BoxedSlice<u8>, CryptoError>;
    extern "C" fn ec_sign_digest<'a>(
        &self,
        curve: EcCurve,
        derivation_path: DerivationPath<'a>,
        digest: Slice<'a, u8>,
    ) -> FastResult<BoxedSlice<u8>, CryptoError>;

    extern "C" fn get_xpub<'a>(
        &self,
        curve: EcCurve,
        derivation_path: DerivationPath<'a>,
    ) -> FastResult<Xpub, CryptoError>;

    extern "C" fn base58_encode<'a>(&self, data: Slice<'a, u8>) -> String;
    extern "C" fn base58_decode<'a>(
        &self,
        data: Str<'a>,
    ) -> FastResult<BoxedSlice<u8>, CryptoError>;
    extern "C" fn base58check_encode<'a>(&self, data: Slice<'a, u8>) -> String;
    extern "C" fn base58check_decode<'a>(
        &self,
        data: Str<'a>,
    ) -> FastResult<BoxedSlice<u8>, CryptoError>;
}

pub type CryptoV1Vtable = stabby::vtable!(CryptoV1 + Send + Sync);
pub type CryptoV1Ref<'a> = stabby::DynRef<'a, CryptoV1Vtable>;

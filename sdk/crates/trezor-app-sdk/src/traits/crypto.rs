use stabby::alloc::string::String;
use stabby::boxed::BoxedSlice;
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

/// Opaque handle to a streaming hash in progress.
///
/// `get_hasher`/`get_hmac_hasher` heap-allocate the hash context and hand
/// back a pointer to it, pinned at that heap address for the hasher's
/// lifetime — any number of hashers, of any mix of algorithms, can be in
/// flight at once. Core owns and interprets the pointee; the app must treat
/// this as opaque, and pass it to `hasher_update` any number of times
/// before passing it to `hasher_finalize` exactly once, which consumes it
/// and frees the underlying allocation. A handle that is never finalized
/// leaks.
#[stabby::stabby]
#[repr(transparent)]
#[derive(Clone, Copy)]
pub struct BoxedHasher(pub *mut u8);

#[stabby::stabby]
#[repr(u8)]
pub enum HashingAlgorithm {
    Sha256,
    Sha3_256,
    Sha512,
    Keccak256,
}

#[stabby::stabby]
#[repr(u8)]
pub enum EcCurve {
    Secp256k1,
    Nist256p1,
    Ed25519,
}

#[stabby::stabby(checked)]
pub trait CryptoV1: Send + Sync {
    extern "C" fn get_hasher(&self, algorithm: HashingAlgorithm) -> BoxedHasher;
    /// Starts an HMAC-SHA256 computation under `key`. `key` is only read
    /// during this call (copied into the HMAC context's internal state);
    /// Core never retains it afterward.
    extern "C" fn get_hmac_hasher<'a>(&self, key: Slice<'a, u8>) -> BoxedHasher;
    extern "C" fn hasher_update<'a>(&self, hasher: BoxedHasher, input: Slice<'a, u8>);
    extern "C" fn hasher_finalize(&self, hasher: BoxedHasher) -> BoxedSlice<u8>;

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
pub type StaticCryptoV1 = CryptoV1Ref<'static>;

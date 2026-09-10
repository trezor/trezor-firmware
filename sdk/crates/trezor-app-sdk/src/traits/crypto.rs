use stabby::alloc::string::String;
use stabby::boxed::{Box, BoxedSlice};
use stabby::option::Option as StabbyOption;
use stabby::slice::Slice;
use stabby::str::Str;

use super::util::FastResult;
use super::wire::WireError;

#[stabby::stabby]
#[repr(u8)]
pub enum CryptoError {
    InvalidPublicKey,
    InvalidSignature,
    InvalidEncoding,
}

impl CryptoError {
    /// Returns a static human-readable description of the error.
    pub fn message(&self) -> &'static str {
        match self {
            Self::InvalidPublicKey => "invalid public key",
            Self::InvalidSignature => "invalid signature",
            Self::InvalidEncoding => "invalid encoding",
        }
    }
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
    extern "C" fn get_hmac<'a>(&self, key: Slice<'a, u8>) -> BoxedHasher;

    /// Derives the extended public key (xpub) for `address_n`.
    extern "C" fn get_xpub<'a>(
        &self,
        address_n: Slice<'a, u32>,
        xpub_magic: u32,
    ) -> FastResult<[u8; 111], WireError>;
    /// Derives the public key for `address_n`.
    extern "C" fn get_public_key<'a>(
        &self,
        address_n: Slice<'a, u32>,
        compressed: bool,
    ) -> FastResult<BoxedSlice<u8>, WireError>;
    /// Signs a 32-byte typed-data hash (e.g. EIP-712) with the key at `address_n`.
    ///
    /// `encoded_network`/`encoded_token` let Core resolve display metadata
    /// for the confirmation prompt; `chain_id` is used for replay
    /// protection. `show_progress` requests a progress indicator while
    /// signing.
    extern "C" fn sign_typed_hash<'a>(
        &self,
        address_n: Slice<'a, u32>,
        hash: [u8; 32],
        encoded_network: StabbyOption<Slice<'a, u8>>,
        encoded_token: StabbyOption<Slice<'a, u8>>,
        chain_id: StabbyOption<u64>,
        show_progress: bool,
    ) -> FastResult<[u8; 65], WireError>;
    /// Signs a raw 32-byte digest with the key at `address_n`.
    extern "C" fn sign_digest<'a>(
        &self,
        address_n: Slice<'a, u32>,
        digest: [u8; 32],
        compressed: bool,
    ) -> FastResult<[u8; 65], WireError>;
    /// Verifies a MAC previously produced by [`Self::get_address_mac`] for
    /// `address_n` and `address`, confirming the pairing hasn't been
    /// tampered with.
    extern "C" fn check_address_mac<'a>(
        &self,
        address_n: Slice<'a, u32>,
        mac: [u8; 32],
        address: Str<'a>,
    ) -> FastResult<bool, WireError>;
    /// Computes a MAC binding `address_n` to `address`, so a cached `address`
    /// can later be re-authenticated via [`Self::check_address_mac`] without
    /// a full re-derivation.
    extern "C" fn get_address_mac<'a>(
        &self,
        address_n: Slice<'a, u32>,
        address: Str<'a>,
    ) -> FastResult<[u8; 32], WireError>;
    /// Checks `nonce` against Core's cached-nonce store, returning whether
    /// it's still valid.
    extern "C" fn verify_nonce_cache<'a>(
        &self,
        nonce: Slice<'a, u8>,
    ) -> FastResult<bool, WireError>;

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

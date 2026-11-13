use stabby::alloc::string::String;
use stabby::boxed::{Box, BoxedSlice};
use stabby::slice::Slice;
use stabby::str::Str;

use super::util::{FastResult, ServiceResult};

/// Length of [`CryptoV1::get_xpub`]'s result: a serialized xpub without its
/// 4-byte version.
pub const XPUB_RAW_LEN: usize = 74;

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
    Sha3_512,
    Keccak512,
}

/// Algorithms accepted by [`CryptoV1::get_hmac`]. A separate (smaller) enum
/// from [`HashingAlgorithm`] since HMAC is only defined here over the SHA-2
/// family, not SHA-3/Keccak.
#[stabby::stabby]
#[repr(u8)]
pub enum HmacAlgorithm {
    Sha256,
    Sha512,
}

/// ECDSA curves. Their values match [`Curve`]'s.
#[stabby::stabby]
#[repr(u8)]
pub enum EcdsaCurve {
    Secp256k1 = 0,
    Nist256p1 = 1,
}

/// Curves to derive keys on. Core only allows the ones in the app's manifest.
#[stabby::stabby]
#[repr(u8)]
pub enum Curve {
    Secp256k1 = 0,
    Nist256p1 = 1,
    Ed25519 = 2,
    Curve25519 = 3,
}

/// Extra constraint on a secp256k1 signature, matching trezor-crypto's
/// `is_canonical` callbacks. Core keeps re-signing until the signature
/// satisfies it.
#[stabby::stabby]
#[repr(u8)]
#[derive(Clone, Copy, PartialEq, Eq)]
pub enum CanonicalSig {
    /// Any valid signature.
    Any = 0,
    /// Ethereum's: the recovery id fits in one bit, and `s` is low.
    Ethereum = 1,
}

#[stabby::stabby(checked)]
pub trait CryptoV1: Send + Sync {
    extern "C" fn get_hasher(&self, algorithm: HashingAlgorithm) -> BoxedHasher;

    /// Starts an HMAC computation (over `algorithm`, one of the SHA-2
    /// family) under `key`. `key` is only read during this call (copied into
    /// the HMAC context's internal state); Core never retains it afterward.
    extern "C" fn get_hmac<'a>(&self, algorithm: HmacAlgorithm, key: Slice<'a, u8>) -> BoxedHasher;

    /// Derives the public node for `address_n` on `curve`, as a serialized
    /// xpub without its version: depth (1), parent fingerprint (4), child
    /// number (4), chain code (32) and compressed public key (33).
    extern "C" fn get_xpub<'a>(
        &self,
        curve: Curve,
        address_n: Slice<'a, u32>,
    ) -> ServiceResult<[u8; XPUB_RAW_LEN], CryptoError>;

    /// Derives the public key for `address_n` on `curve`.
    extern "C" fn get_public_key<'a>(
        &self,
        curve: Curve,
        address_n: Slice<'a, u32>,
        compressed: bool,
    ) -> ServiceResult<BoxedSlice<u8>, CryptoError>;

    /// Signs a raw 32-byte digest with the ECDSA key at `address_n`; Ed25519
    /// has no digest signing, see [`Self::ed25519_sign`].
    ///
    /// `canonical` is only supported on secp256k1; any other curve rejects
    /// anything but [`CanonicalSig::Any`].
    extern "C" fn ecdsa_sign_digest<'a>(
        &self,
        curve: EcdsaCurve,
        address_n: Slice<'a, u32>,
        digest: &'a [u8; 32],
        compressed: bool,
        canonical: CanonicalSig,
    ) -> ServiceResult<[u8; 65], CryptoError>;

    /// Signs `message` with the Ed25519 key at `address_n`.
    extern "C" fn ed25519_sign<'a>(
        &self,
        address_n: Slice<'a, u32>,
        message: Slice<'a, u8>,
    ) -> ServiceResult<[u8; 64], CryptoError>;

    /// Verifies a MAC previously produced by [`Self::get_address_mac`] for
    /// `address_n`, `address` and the coin type `slip44`, confirming the
    /// pairing hasn't been tampered with. Fails on a wrong MAC.
    extern "C" fn check_address_mac<'a>(
        &self,
        address_n: Slice<'a, u32>,
        mac: &'a [u8; 32],
        address: Str<'a>,
        slip44: u32,
    ) -> ServiceResult<(), CryptoError>;

    /// Computes a MAC binding `address_n` to `address` of the coin type
    /// `slip44`, so a cached `address` can later be re-authenticated via
    /// [`Self::check_address_mac`] without a full re-derivation.
    extern "C" fn get_address_mac<'a>(
        &self,
        address_n: Slice<'a, u32>,
        address: Str<'a>,
        slip44: u32,
    ) -> ServiceResult<[u8; 32], CryptoError>;

    /// Verifies a 64-byte `r||s` ECDSA `signature` of `digest` against
    /// `public_key`, given in compressed or uncompressed SEC1 form.
    extern "C" fn ecdsa_verify_digest<'a>(
        &self,
        curve: EcdsaCurve,
        public_key: Slice<'a, u8>,
        signature: Slice<'a, u8>,
        digest: Slice<'a, u8>,
    ) -> FastResult<(), CryptoError>;

    /// Recovers the uncompressed public key from an ECDSA `signature` over
    /// `digest`, with no candidate public key to check against (unlike
    /// [`Self::ecdsa_verify_digest`], which confirms `signature` matches a
    /// given key — this instead always returns whichever key the signature's
    /// own recovery id points to). `signature` is 65 bytes: a 1-byte recovery
    /// id (`0..=3`) followed by the 64-byte `r||s` signature (Trezor's
    /// `[v, r, s]` convention).
    extern "C" fn ecdsa_recover_pubkey<'a>(
        &self,
        curve: EcdsaCurve,
        signature: Slice<'a, u8>,
        digest: Slice<'a, u8>,
    ) -> FastResult<BoxedSlice<u8>, CryptoError>;

    /// Verifies a 64-byte Ed25519 `signature` of `message` against the
    /// 32-byte `public_key`.
    extern "C" fn ed25519_verify<'a>(
        &self,
        public_key: Slice<'a, u8>,
        signature: Slice<'a, u8>,
        message: Slice<'a, u8>,
    ) -> FastResult<(), CryptoError>;

    /// Base58-encodes `data`.
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

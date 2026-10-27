//! High-level crypto API
//!
//! This module provides user-friendly functions for interacting with the Trezor crypto.
//!
//! [`get_address_mac`] and friends round-trip through Core over IPC (via the
//! stable-ABI [`CryptoV1`](crate::traits::crypto::CryptoV1) vtable handed to
//! this app), since they touch key material Core alone holds.
//!
//! [`get_hasher`]/[`get_hmac`] are local (non-IPC) — hashing needs no secret
//! material, so instead of Core they call straight through the local
//! `CryptoV1::get_hasher`/`get_hmac` vtable, returning a [`BoxedHasher`]:
//! update it and read the digest via [`HasherExt`], which — unlike the
//! underlying stable-ABI [`Hasher`](crate::traits::crypto::Hasher) trait —
//! takes/returns plain `&[u8]`/[`BoxedSlice<u8>`], so call sites don't need
//! their own dependency on `stabby` (the SDK crate is the only dependency
//! apps should need).

use stabby::boxed::BoxedSlice;
use stabby::slice::Slice;

use crate::alloc_types::{String, Vec};
use crate::app_runtime::get_crypto_or_die;
pub use crate::traits::crypto::{
    BoxedHasher, CanonicalSig, EcdsaCurve, HashingAlgorithm, HmacAlgorithm,
};
use crate::traits::crypto::{CryptoV1Dyn as _, HasherDynMut};
use crate::{IntoAppResult, Result, ResultExt};

/// A local (non-IPC) streaming hasher for `algorithm` — see the module docs.
pub fn get_hasher(algorithm: HashingAlgorithm) -> BoxedHasher {
    get_crypto_or_die().get_hasher(algorithm)
}

/// A local (non-IPC) HMAC hasher (over `algorithm`, one of the SHA-2 family)
/// keyed with `key` — see the module docs.
pub fn get_hmac(algorithm: HmacAlgorithm, key: &[u8]) -> BoxedHasher {
    get_crypto_or_die().get_hmac(algorithm, key.into())
}

/// Ergonomic, `stabby`-free wrapper around [`BoxedHasher`]'s stable-ABI
/// methods — see the module docs.
pub trait HasherExt {
    /// Feeds more input into the hash state.
    fn update(&mut self, input: &[u8]);
    /// Writes the final digest, consuming accumulated state.
    fn finalize(&mut self) -> BoxedSlice<u8>;
}

impl HasherExt for BoxedHasher {
    fn update(&mut self, input: &[u8]) {
        HasherDynMut::update(self, Slice::from(input));
    }

    fn finalize(&mut self) -> BoxedSlice<u8> {
        HasherDynMut::finalize(self)
    }
}

/// Derives the extended public key (xpub) for `address_n`, base58check-encoded
/// with `xpub_magic` as its version bytes (e.g. the "xpub"/"ypub"/"zpub"
/// prefix bytes for the coin/script type in use).
pub fn get_xpub(address_n: &[u32], xpub_magic: u32) -> Result<[u8; 111]> {
    get_crypto_or_die()
        .get_xpub(address_n.into(), xpub_magic)
        .into_app_result()
        .c()
}

/// Derives the public key for `address_n`.
pub fn get_public_key(address_n: &[u32], compressed: bool) -> Result<Vec<u8>> {
    get_crypto_or_die()
        .get_public_key(address_n.into(), compressed)
        .into_app_result()
        .c()
        .map(|b| b.as_ref().to_vec())
}

/// Signs a raw 32-byte digest with the ECDSA key at `address_n`, returning
/// the 65-byte recoverable signature. Ed25519 has no digest signing, see
/// [`ed25519_sign`].
///
/// `canonical` constrains a secp256k1 signature further, e.g.
/// [`CanonicalSig::Ethereum`] for Ethereum transactions and messages. Other
/// curves only accept [`CanonicalSig::Any`].
pub fn ecdsa_sign_digest(
    address_n: &[u32],
    digest: &[u8; 32],
    compressed: bool,
    canonical: CanonicalSig,
) -> Result<[u8; 65]> {
    get_crypto_or_die()
        .ecdsa_sign_digest(address_n.into(), digest, compressed, canonical)
        .into_app_result()
        .c()
}

/// Signs `message` with the Ed25519 key at `address_n`.
pub fn ed25519_sign(address_n: &[u32], message: &[u8]) -> Result<[u8; 64]> {
    get_crypto_or_die()
        .ed25519_sign(address_n.into(), message.into())
        .into_app_result()
        .c()
}

/// Verifies a MAC previously produced by [`get_address_mac`] for `address_n`,
/// `address` and the coin type `slip44`, confirming the pairing hasn't been
/// tampered with. Fails on a wrong MAC.
pub fn check_address_mac(
    address_n: &[u32],
    mac: &[u8; 32],
    address: &str,
    slip44: u32,
) -> Result<()> {
    get_crypto_or_die()
        .check_address_mac(address_n.into(), mac, address.into(), slip44)
        .into_app_result()
        .c()
}

/// Computes a MAC binding `address_n` to `address` of the coin type `slip44`
/// (as the built-in coin apps do), so a cached `address` can later be
/// re-authenticated via [`check_address_mac`] without a full re-derivation.
pub fn get_address_mac(address_n: &[u32], address: &str, slip44: u32) -> Result<[u8; 32]> {
    get_crypto_or_die()
        .get_address_mac(address_n.into(), address.into(), slip44)
        .into_app_result()
        .c()
}

/// Checks `nonce` against Core's cached-nonce store, returning whether it's still valid.
pub fn verify_nonce_cache(nonce: &[u8]) -> Result<bool> {
    get_crypto_or_die()
        .verify_nonce_cache(nonce.into())
        .into_app_result()
        .c()
}

/// Verifies a 64-byte `r||s` ECDSA `signature` of `digest` against
/// `public_key` (compressed or uncompressed SEC1).
pub fn ecdsa_verify_digest(
    curve: EcdsaCurve,
    public_key: &[u8],
    signature: &[u8],
    digest: &[u8],
) -> Result<()> {
    get_crypto_or_die()
        .ecdsa_verify_digest(curve, public_key.into(), signature.into(), digest.into())
        .into_app_result()
        .c()
}

/// Recovers the uncompressed public key from an ECDSA `signature` over
/// `digest`, with no candidate public key to check against — see
/// [`traits::crypto::CryptoV1::ecdsa_recover_pubkey`](crate::traits::crypto::CryptoV1::ecdsa_recover_pubkey)
/// for `signature`'s exact byte layout.
pub fn ecdsa_recover_pubkey(curve: EcdsaCurve, signature: &[u8], digest: &[u8]) -> Result<Vec<u8>> {
    get_crypto_or_die()
        .ecdsa_recover_pubkey(curve, signature.into(), digest.into())
        .into_app_result()
        .c()
        .map(|b| b.as_ref().to_vec())
}

/// Verifies a 64-byte Ed25519 `signature` of `message` against the 32-byte
/// `public_key`.
pub fn ed25519_verify(public_key: &[u8], signature: &[u8], message: &[u8]) -> Result<()> {
    get_crypto_or_die()
        .ed25519_verify(public_key.into(), signature.into(), message.into())
        .into_app_result()
        .c()
}

/// Verifies a CoSi (collective Ed25519) `signature` of `message` against
/// `public_keys`, combining the ones selected by `sigmask` (bit 0 = first
/// key) and requiring at least `threshold` of them to have participated.
pub fn cosi_verify(
    threshold: u8,
    message: &[u8],
    public_keys: &[[u8; 32]],
    sigmask: u8,
    signature: &[u8],
) -> Result<()> {
    get_crypto_or_die()
        .cosi_verify(
            threshold,
            message.into(),
            public_keys.into(),
            sigmask,
            signature.into(),
        )
        .into_app_result()
        .c()
}

/// Combines `public_keys` into the single Ed25519 public key that a CoSi
/// signature over their combination would verify against — the same
/// combining step [`cosi_verify`] performs internally, exposed standalone for
/// callers that need the combined key itself (e.g. to cache it) rather than
/// an immediate verify.
pub fn cosi_combine_publickeys(public_keys: &[[u8; 32]]) -> Result<[u8; 32]> {
    get_crypto_or_die()
        .cosi_combine_publickeys(public_keys.into())
        .into_app_result()
        .c()
}

/// Base58-encodes `data`.
pub fn base58_encode(data: &[u8]) -> Result<String> {
    get_crypto_or_die()
        .base58_encode(data.into())
        .into_app_result()
        .c()
        .map(|s| String::from(s.as_str()))
}

/// Decodes a base58-encoded `data` string.
pub fn base58_decode(data: &str) -> Result<Vec<u8>> {
    get_crypto_or_die()
        .base58_decode(data.into())
        .into_app_result()
        .c()
        .map(|b| b.as_ref().to_vec())
}

/// Base58Check-encodes `data` (base58 plus a 4-byte checksum).
pub fn base58check_encode(data: &[u8]) -> Result<String> {
    get_crypto_or_die()
        .base58check_encode(data.into())
        .into_app_result()
        .c()
        .map(|s| String::from(s.as_str()))
}

/// Decodes a base58Check-encoded `data` string, verifying its checksum.
pub fn base58check_decode(data: &str) -> Result<Vec<u8>> {
    get_crypto_or_die()
        .base58check_decode(data.into())
        .into_app_result()
        .c()
        .map(|b| b.as_ref().to_vec())
}

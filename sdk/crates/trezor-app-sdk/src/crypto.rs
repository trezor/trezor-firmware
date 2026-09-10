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

pub use crate::traits::crypto::{BoxedHasher, HashingAlgorithm};

use stabby::boxed::BoxedSlice;
use stabby::slice::Slice;

use crate::alloc_types::{String, Vec};
use crate::app_runtime2::get_crypto_or_die;
use crate::traits::crypto::{CryptoV1Dyn as _, EcCurve, HasherDynMut};
use crate::{IntoAppResult, Result, ResultExt};

/// A local (non-IPC) streaming hasher for `algorithm` — see the module docs.
pub fn get_hasher(algorithm: HashingAlgorithm) -> BoxedHasher {
    get_crypto_or_die().get_hasher(algorithm)
}

/// A local (non-IPC) HMAC-SHA256 hasher keyed with `key` — see the module docs.
pub fn get_hmac(key: &[u8]) -> BoxedHasher {
    get_crypto_or_die().get_hmac(key.into())
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

/// Signs a 32-byte typed-data hash (e.g. EIP-712) with the key at `address_n`.
///
/// `encoded_network`/`encoded_token` let Core resolve display metadata for
/// the confirmation prompt; `chain_id` is used for replay protection.
/// `show_progress` requests a progress indicator while signing.
pub fn sign_typed_hash(
    address_n: &[u32],
    hash: &[u8; 32],
    encoded_network: Option<&[u8]>,
    encoded_token: Option<&[u8]>,
    chain_id: Option<u64>,
    show_progress: bool,
) -> Result<[u8; 65]> {
    get_crypto_or_die()
        .sign_typed_hash(
            address_n.into(),
            *hash,
            encoded_network.map(Into::into).into(),
            encoded_token.map(Into::into).into(),
            chain_id.into(),
            show_progress,
        )
        .into_app_result()
        .c()
}

/// Signs a raw 32-byte digest with the key at `address_n`.
pub fn sign_digest(address_n: &[u32], digest: &[u8; 32], compressed: bool) -> Result<[u8; 65]> {
    get_crypto_or_die()
        .sign_digest(address_n.into(), *digest, compressed)
        .into_app_result()
        .c()
}

/// Verifies a MAC previously produced by [`get_address_mac`] for `address_n`
/// and `address`, confirming the pairing hasn't been tampered with.
pub fn check_address_mac(address_n: &[u32], mac: &[u8; 32], address: &str) -> Result<bool> {
    get_crypto_or_die()
        .check_address_mac(address_n.into(), *mac, address.into())
        .into_app_result()
        .c()
}

/// Computes a MAC binding `address_n` to `address`, so a cached `address` can
/// later be re-authenticated via [`check_address_mac`] without a full re-derivation.
pub fn get_address_mac(address_n: &[u32], address: &str) -> Result<[u8; 32]> {
    get_crypto_or_die()
        .get_address_mac(address_n.into(), address.into())
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

/// Recovers the public key from `signature` over `message` (hashed with
/// SHA-256 for the Weierstrass curves) and confirms it matches `public_key`.
pub fn ec_verify_recover(
    curve: EcCurve,
    public_key: &[u8],
    signature: &[u8],
    message: &[u8],
) -> Result<Vec<u8>> {
    get_crypto_or_die()
        .ec_verify_recover(curve, public_key.into(), signature.into(), message.into())
        .into_app_result()
        .c()
        .map(|b| b.as_ref().to_vec())
}

/// Like [`ec_verify_recover`], but takes an already-hashed `digest` directly.
pub fn ec_verify_recover_digest(
    curve: EcCurve,
    public_key: &[u8],
    signature: &[u8],
    digest: &[u8],
) -> Result<Vec<u8>> {
    get_crypto_or_die()
        .ec_verify_recover_digest(curve, public_key.into(), signature.into(), digest.into())
        .into_app_result()
        .c()
        .map(|b| b.as_ref().to_vec())
}

/// Base58-encodes `data`.
pub fn base58_encode(data: &[u8]) -> String {
    String::from(get_crypto_or_die().base58_encode(data.into()).as_ref())
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
pub fn base58check_encode(data: &[u8]) -> String {
    String::from(get_crypto_or_die().base58check_encode(data.into()).as_ref())
}

/// Decodes a base58Check-encoded `data` string, verifying its checksum.
pub fn base58check_decode(data: &str) -> Result<Vec<u8>> {
    get_crypto_or_die()
        .base58check_decode(data.into())
        .into_app_result()
        .c()
        .map(|b| b.as_ref().to_vec())
}

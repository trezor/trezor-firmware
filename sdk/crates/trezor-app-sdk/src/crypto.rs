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
//! takes and returns plain bytes (`&[u8]`, `impl AsRef<[u8]>`), so call sites don't need
//! their own dependency on `stabby` (the SDK crate is the only dependency
//! apps should need).

use alloc::string::String;
use alloc::vec::Vec;

use stabby::slice::Slice;

use crate::app_runtime::get_crypto_or_die;
pub use crate::traits::crypto::{
    BoxedHasher, CanonicalSig, Curve, EcdsaCurve, HashingAlgorithm, HmacAlgorithm, XPUB_RAW_LEN,
};
use crate::traits::crypto::{CryptoV1Dyn as _, HasherDynMut};
use crate::util::Bytes;
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
    /// Returns the digest. Consumes the hasher, so it can't be used again:
    ///
    /// ```compile_fail
    /// # use trezor_app_sdk::crypto::{self, HasherExt, HashingAlgorithm};
    /// let mut hasher = crypto::get_hasher(HashingAlgorithm::Sha256);
    /// hasher.finalize();
    /// hasher.update(b"more");
    /// ```
    fn finalize(self) -> impl AsRef<[u8]>;
}

impl HasherExt for BoxedHasher {
    fn update(&mut self, input: &[u8]) {
        HasherDynMut::update(self, Slice::from(input));
    }

    fn finalize(mut self) -> impl AsRef<[u8]> {
        Bytes(HasherDynMut::finalize(&mut self))
    }
}

/// A derived public node: the fields of a serialized xpub.
#[derive(Clone, PartialEq, Eq)]
pub struct PublicNode {
    pub depth: u8,
    /// Fingerprint of the parent node.
    pub fingerprint: u32,
    pub child_num: u32,
    pub chain_code: [u8; 32],
    /// Compressed public key.
    pub public_key: [u8; 33],
}

impl PublicNode {
    fn from_raw(raw: &[u8; XPUB_RAW_LEN]) -> Self {
        let (depth, rest) = raw.split_at(1);
        let (fingerprint, rest) = rest.split_at(4);
        let (child_num, rest) = rest.split_at(4);
        let (chain_code, public_key) = rest.split_at(32);
        Self {
            depth: depth[0],
            fingerprint: u32::from_be_bytes(fingerprint.try_into().unwrap_or_default()),
            child_num: u32::from_be_bytes(child_num.try_into().unwrap_or_default()),
            chain_code: chain_code.try_into().unwrap_or_default(),
            public_key: public_key.try_into().unwrap_or([0; 33]),
        }
    }

    /// The node serialized as an xpub with `version` as its version bytes,
    /// before base58check encoding.
    pub fn serialize(&self, version: u32) -> [u8; 4 + XPUB_RAW_LEN] {
        let mut data = [0u8; 4 + XPUB_RAW_LEN];
        data[..4].copy_from_slice(&version.to_be_bytes());
        data[4] = self.depth;
        data[5..9].copy_from_slice(&self.fingerprint.to_be_bytes());
        data[9..13].copy_from_slice(&self.child_num.to_be_bytes());
        data[13..45].copy_from_slice(&self.chain_code);
        data[45..].copy_from_slice(&self.public_key);
        data
    }

    /// The node as a base58check xpub with `version` as its version bytes
    /// (e.g. the "xpub"/"ypub"/"zpub" prefix for the coin/script type in use).
    pub fn to_xpub(&self, version: u32) -> String {
        base58check_encode(&self.serialize(version))
    }
}

/// Derives the public node for `address_n` on `curve`.
pub fn get_public_node(curve: Curve, address_n: &[u32]) -> Result<PublicNode> {
    get_crypto_or_die()
        .get_xpub(curve, address_n.into())
        .into_app_result()
        .c()
        .map(|raw| PublicNode::from_raw(&raw))
}

/// Derives the extended public key (xpub) for `address_n` on `curve`,
/// base58check-encoded with `version` as its version bytes (e.g. the
/// "xpub"/"ypub"/"zpub" prefix bytes for the coin/script type in use).
pub fn get_xpub(curve: Curve, address_n: &[u32], version: u32) -> Result<String> {
    Ok(get_public_node(curve, address_n)?.to_xpub(version))
}

/// Derives the public key for `address_n` on `curve`.
pub fn get_public_key(curve: Curve, address_n: &[u32], compressed: bool) -> Result<Vec<u8>> {
    get_crypto_or_die()
        .get_public_key(curve, address_n.into(), compressed)
        .into_app_result()
        .c()
        .map(|b| b.as_ref().to_vec())
}

/// Signs a raw 32-byte digest with the ECDSA key at `address_n` on `curve`,
/// returning the 65-byte recoverable signature. Ed25519 has no digest
/// signing, see [`ed25519_sign`].
///
/// `canonical` constrains a secp256k1 signature further, e.g.
/// [`CanonicalSig::Ethereum`] for Ethereum transactions and messages. Other
/// curves only accept [`CanonicalSig::Any`].
pub fn ecdsa_sign_digest(
    curve: EcdsaCurve,
    address_n: &[u32],
    digest: &[u8; 32],
    compressed: bool,
    canonical: CanonicalSig,
) -> Result<[u8; 65]> {
    get_crypto_or_die()
        .ecdsa_sign_digest(curve, address_n.into(), digest, compressed, canonical)
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

/// Base58-encodes `data`.
pub fn base58_encode(data: &[u8]) -> String {
    String::from(get_crypto_or_die().base58_encode(data.into()).as_str())
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
    String::from(get_crypto_or_die().base58check_encode(data.into()).as_str())
}

/// Decodes a base58Check-encoded `data` string, verifying its checksum.
pub fn base58check_decode(data: &str) -> Result<Vec<u8>> {
    get_crypto_or_die()
        .base58check_decode(data.into())
        .into_app_result()
        .c()
        .map(|b| b.as_ref().to_vec())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn public_node_layout() {
        let mut raw = [0u8; XPUB_RAW_LEN];
        raw[0] = 3;
        raw[1..5].copy_from_slice(&0x0102_0304u32.to_be_bytes());
        raw[5..9].copy_from_slice(&0x8000_002cu32.to_be_bytes());
        raw[9..41].fill(0xcc);
        raw[41] = 0x02;
        raw[42..].fill(0xaa);

        let node = PublicNode::from_raw(&raw);
        assert_eq!(node.depth, 3);
        assert_eq!(node.fingerprint, 0x0102_0304);
        assert_eq!(node.child_num, 0x8000_002c);
        assert_eq!(node.chain_code, [0xcc; 32]);
        assert_eq!(node.public_key[0], 0x02);
        assert_eq!(node.public_key[1..], [0xaa; 32]);

        let serialized = node.serialize(0x0488_b21e);
        assert_eq!(serialized[..4], 0x0488_b21eu32.to_be_bytes());
        assert_eq!(serialized[4..], raw);
    }
}

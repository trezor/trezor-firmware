//! One handler per SDK crypto function: convert the request's parameters to
//! the function's types, call it, and hand its result back.
//!
//! A parameter the function's types can't hold (a digest that isn't 32 bytes,
//! a sigmask over 255, an unknown enum value) is refused with
//! `InvalidArgument` before the function is called; every other error is the
//! function's own.

use trezor_app_sdk::crypto::{
    self as sdk, CanonicalSig, EcdsaCurve, HasherExt, HashingAlgorithm, HmacAlgorithm,
};
use trezor_app_sdk::{Error, Result};

use crate::alloc_types::{String, Vec};
use crate::proto::testapp as wire;

// ============================================================================
// Hashing
// ============================================================================

pub fn hash(m: wire::Hash) -> Result<wire::Digest> {
    let algorithm = match wire::HashAlgorithm::try_from(m.algorithm) {
        Ok(wire::HashAlgorithm::Sha256) => HashingAlgorithm::Sha256,
        Ok(wire::HashAlgorithm::Sha3256) => HashingAlgorithm::Sha3_256,
        Ok(wire::HashAlgorithm::Sha512) => HashingAlgorithm::Sha512,
        Ok(wire::HashAlgorithm::Keccak256) => HashingAlgorithm::Keccak256,
        Ok(wire::HashAlgorithm::Sha3512) => HashingAlgorithm::Sha3_512,
        Ok(wire::HashAlgorithm::Keccak512) => HashingAlgorithm::Keccak512,
        Err(_) => return Err(Error::InvalidArgument),
    };
    let mut hasher = sdk::get_hasher(algorithm);
    Ok(digest(&mut hasher, &m.chunks))
}

pub fn hmac(m: wire::Hmac) -> Result<wire::Digest> {
    let algorithm = match wire::HmacAlgorithm::try_from(m.algorithm) {
        Ok(wire::HmacAlgorithm::HmacSha256) => HmacAlgorithm::Sha256,
        Ok(wire::HmacAlgorithm::HmacSha512) => HmacAlgorithm::Sha512,
        Err(_) => return Err(Error::InvalidArgument),
    };
    let mut hasher = sdk::get_hmac(algorithm, &m.key);
    Ok(digest(&mut hasher, &m.chunks))
}

fn digest(hasher: &mut sdk::BoxedHasher, chunks: &[Vec<u8>]) -> wire::Digest {
    for chunk in chunks {
        hasher.update(chunk);
    }
    wire::Digest {
        digest: hasher.finalize().as_ref().to_vec(),
    }
}

// ============================================================================
// Keys and signatures (served by Core)
// ============================================================================

pub fn get_xpub(m: wire::GetXpub) -> Result<wire::Xpub> {
    let xpub = sdk::get_xpub(&m.address_n, m.xpub_magic)?;
    let xpub = String::from_utf8(xpub.to_vec()).map_err(|_| Error::InvalidMessage)?;
    Ok(wire::Xpub { xpub })
}

pub fn get_public_key(m: wire::GetPublicKey) -> Result<wire::PublicKey> {
    let public_key = sdk::get_public_key(&m.address_n, m.compressed)?;
    Ok(wire::PublicKey { public_key })
}

pub fn ecdsa_sign_digest(m: wire::EcdsaSignDigest) -> Result<wire::Signature> {
    let signature = sdk::ecdsa_sign_digest(
        &m.address_n,
        array(&m.digest)?,
        m.compressed,
        canonical(m.canonical)?,
    )?;
    Ok(wire::Signature {
        signature: signature.to_vec(),
    })
}

pub fn ed25519_sign(m: wire::Ed25519Sign) -> Result<wire::Signature> {
    let signature = sdk::ed25519_sign(&m.address_n, &m.message)?;
    Ok(wire::Signature {
        signature: signature.to_vec(),
    })
}

pub fn get_address_mac(m: wire::GetAddressMac) -> Result<wire::AddressMac> {
    let mac = sdk::get_address_mac(&m.address_n, &m.address, m.slip44)?;
    Ok(wire::AddressMac { mac: mac.to_vec() })
}

pub fn check_address_mac(m: wire::CheckAddressMac) -> Result<wire::Success> {
    sdk::check_address_mac(&m.address_n, array(&m.mac)?, &m.address, m.slip44)?;
    Ok(wire::Success {})
}

pub fn verify_nonce_cache(m: wire::VerifyNonceCache) -> Result<wire::Bool> {
    let value = sdk::verify_nonce_cache(&m.nonce)?;
    Ok(wire::Bool { value })
}

// ============================================================================
// Signature verification and key recovery
// ============================================================================

/// `ecdsa_verify_digest` of the message's SHA-256 digest.
pub fn ecdsa_verify(m: wire::EcdsaVerify) -> Result<wire::Success> {
    let mut hasher = sdk::get_hasher(HashingAlgorithm::Sha256);
    hasher.update(&m.message);
    let digest = hasher.finalize();
    sdk::ecdsa_verify_digest(curve(m.curve)?, &m.public_key, &m.signature, &digest)?;
    Ok(wire::Success {})
}

pub fn ecdsa_verify_digest(m: wire::EcdsaVerifyDigest) -> Result<wire::Success> {
    sdk::ecdsa_verify_digest(curve(m.curve)?, &m.public_key, &m.signature, &m.digest)?;
    Ok(wire::Success {})
}

pub fn ecdsa_recover_pubkey(m: wire::EcdsaRecoverPubkey) -> Result<wire::PublicKey> {
    let public_key = sdk::ecdsa_recover_pubkey(curve(m.curve)?, &m.signature, &m.digest)?;
    Ok(wire::PublicKey { public_key })
}

pub fn ed25519_verify(m: wire::Ed25519Verify) -> Result<wire::Success> {
    sdk::ed25519_verify(&m.public_key, &m.signature, &m.message)?;
    Ok(wire::Success {})
}

fn canonical(value: i32) -> Result<CanonicalSig> {
    match wire::CanonicalSig::try_from(value) {
        Ok(wire::CanonicalSig::Any) => Ok(CanonicalSig::Any),
        Ok(wire::CanonicalSig::Ethereum) => Ok(CanonicalSig::Ethereum),
        Err(_) => Err(Error::InvalidArgument),
    }
}

fn curve(value: i32) -> Result<EcdsaCurve> {
    match wire::EcdsaCurve::try_from(value) {
        Ok(wire::EcdsaCurve::Secp256k1) => Ok(EcdsaCurve::Secp256k1),
        Ok(wire::EcdsaCurve::Nist256p1) => Ok(EcdsaCurve::Nist256p1),
        Err(_) => Err(Error::InvalidArgument),
    }
}

// ============================================================================
// CoSi
// ============================================================================

pub fn cosi_verify(m: wire::CosiVerify) -> Result<wire::Success> {
    let threshold = u8::try_from(m.threshold).map_err(|_| Error::InvalidArgument)?;
    let sigmask = u8::try_from(m.sigmask).map_err(|_| Error::InvalidArgument)?;
    let public_keys = public_keys(&m.public_keys)?;
    sdk::cosi_verify(threshold, &m.message, &public_keys, sigmask, &m.signature)?;
    Ok(wire::Success {})
}

pub fn cosi_combine_publickeys(m: wire::CosiCombinePublicKeys) -> Result<wire::PublicKey> {
    let public_key = sdk::cosi_combine_publickeys(&public_keys(&m.public_keys)?)?;
    Ok(wire::PublicKey {
        public_key: public_key.to_vec(),
    })
}

fn public_keys(keys: &[Vec<u8>]) -> Result<Vec<[u8; 32]>> {
    keys.iter().map(|key| array(key).copied()).collect()
}

// ============================================================================
// Base58
// ============================================================================

pub fn base58_encode(m: wire::Base58Encode) -> Result<wire::Base58> {
    let encoded = sdk::base58_encode(&m.data)?;
    Ok(wire::Base58 { encoded })
}

pub fn base58_decode(m: wire::Base58Decode) -> Result<wire::Data> {
    let data = sdk::base58_decode(&m.encoded)?;
    Ok(wire::Data { data })
}

pub fn base58check_encode(m: wire::Base58CheckEncode) -> Result<wire::Base58> {
    let encoded = sdk::base58check_encode(&m.data)?;
    Ok(wire::Base58 { encoded })
}

pub fn base58check_decode(m: wire::Base58CheckDecode) -> Result<wire::Data> {
    let data = sdk::base58check_decode(&m.encoded)?;
    Ok(wire::Data { data })
}

// ============================================================================
// Helpers
// ============================================================================

/// `bytes` as a fixed-size array, or `InvalidArgument` if the length differs.
fn array<const N: usize>(bytes: &[u8]) -> Result<&[u8; N]> {
    bytes.try_into().map_err(|_| Error::InvalidArgument)
}

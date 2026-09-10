use rkyv::rancor::Failure;
use rkyv::to_bytes;
use stabby::boxed::BoxedSlice;
use stabby::option::Option as StabbyOption;
use stabby::slice::Slice;
use stabby::str::Str;
use stabby::string::String;
use trezor_app_sdk::structs::{TrezorCryptoEnum, TrezorCryptoResultRef};
use trezor_app_sdk::traits::crypto::{
    BoxedHasher, CryptoError, CryptoV1, EcCurve, HashingAlgorithm,
};
use trezor_app_sdk::traits::util::{FastResult, TIMEOUT_MAX};
use trezor_app_sdk::traits::wire::WireError;

use crate::wire::{CoreIpcService, ipc_call};

mod hashers;

/// Serializes `value` and sends it to Core's crypto service, returning the
/// raw response bytes. Callers deserialize themselves — each `CryptoV1`
/// method knows exactly which [`TrezorCryptoResultRef`] variant to expect
/// and extracts it directly from the archived form, rather than
/// round-tripping through an owned intermediate (`PublicKey`'s payload
/// borrows from the archived buffer, so there is no single owned shape that
/// fits every variant).
fn ipc_crypto_call(value: &TrezorCryptoEnum) -> Result<&'static [u8], WireError> {
    let bytes = to_bytes::<Failure>(value).map_err(|_| WireError::DecodeError)?;
    let (_id, data) = ipc_call(CoreIpcService::Crypto.into(), value.id() as u16, &bytes, TIMEOUT_MAX)?;
    Ok(data)
}

/// Maps an [`EcCurve`] to the Weierstrass curve `crypto::ecdsa` understands.
/// `None` for `Ed25519`, which isn't a Weierstrass curve and has no ECDSA
/// recovery scheme.
fn ecdsa_curve(curve: EcCurve) -> Option<crypto::ecdsa::Curve> {
    match curve {
        EcCurve::Secp256k1 => Some(crypto::ecdsa::Curve::Secp256k1),
        EcCurve::Nist256p1 => Some(crypto::ecdsa::Curve::Nist256p1),
        EcCurve::Ed25519 => None,
    }
}

/// Single-round SHA-256 of `data` — the digest algorithm `ec_verify_recover`
/// uses to turn a `message` into the digest ECDSA recovery operates on.
/// Coin-specific message framing (e.g. Bitcoin's magic-prefixed
/// double-SHA256) is the caller's job; this is deliberately just a plain hash.
fn sha256_digest(data: &[u8]) -> [u8; crypto::sha256::DIGEST_SIZE] {
    crypto::sha256::Sha256::digest(data)
}

/// Compresses an uncompressed (0x04-prefixed, 65-byte) SEC1 public key into
/// its 33-byte compressed (0x02/0x03-prefixed) form.
fn compress_pubkey(uncompressed: &crypto::ecdsa::EcdsaPublicKey) -> [u8; 33] {
    let mut out = [0u8; 33];
    out[0] = 0x02 | (uncompressed[64] & 1);
    out[1..].copy_from_slice(&uncompressed[1..33]);
    out
}

/// Whether `recovered` (always uncompressed) equals `expected`, which may be
/// given in either compressed or uncompressed SEC1 form.
fn pubkey_matches(recovered: &crypto::ecdsa::EcdsaPublicKey, expected: &[u8]) -> bool {
    match expected.len() {
        65 => expected == &recovered[..],
        33 => expected == &compress_pubkey(recovered)[..],
        _ => false,
    }
}

/// Shared implementation for `ec_verify_recover`/`ec_verify_recover_digest`:
/// tries every ECDSA recovery id against `digest`, and if any recovered
/// pubkey matches `public_key`, returns `public_key` back as confirmation.
fn ecdsa_verify_recover_digest(
    curve: EcCurve,
    public_key: &[u8],
    signature: &[u8],
    digest: &[u8],
) -> Result<BoxedSlice<u8>, CryptoError> {
    let Some(curve) = ecdsa_curve(curve) else {
        return Err(CryptoError::InvalidSignature);
    };
    let signature: &crypto::ecdsa::EcdsaSignature = signature
        .try_into()
        .map_err(|_| CryptoError::InvalidEncoding)?;
    let digest: &crypto::ecdsa::EcdsaDigest = digest
        .try_into()
        .map_err(|_| CryptoError::InvalidEncoding)?;

    for recid in 0..4u8 {
        if let Ok(recovered) =
            crypto::ecdsa::verify_recover(curve, signature, crypto::ecdsa::RecId::new(recid), digest)
        {
            if pubkey_matches(&recovered, public_key) {
                return Ok(BoxedSlice::from(public_key));
            }
        }
    }
    Err(CryptoError::InvalidSignature)
}

pub struct TrezorCryptoV1Impl;

impl CryptoV1 for TrezorCryptoV1Impl {
    extern "C" fn get_hasher(&self, algorithm: HashingAlgorithm) -> BoxedHasher {
        match algorithm {
            HashingAlgorithm::Sha256 => hashers::Sha256::new().into(),
            HashingAlgorithm::Sha512 => hashers::Sha512::new().into(),
            HashingAlgorithm::Sha3_256 => hashers::Sha3::new(256, false).into(),
            HashingAlgorithm::Keccak256 => hashers::Sha3::new(256, true).into(),
        }
    }

    extern "C" fn get_hmac<'a>(&self, key: Slice<'a, u8>) -> BoxedHasher {
        hashers::HmacSha256::new(key.as_slice()).into()
    }

    extern "C" fn get_xpub<'a>(
        &self,
        address_n: Slice<'a, u32>,
        xpub_magic: u32,
    ) -> FastResult<[u8; 111], WireError> {
        (|| {
            let data = ipc_crypto_call(&TrezorCryptoEnum::GetXpub {
                address_n: address_n.as_slice().into(),
                xpub_magic,
            })?;
            let archived = rkyv::access::<rkyv::Archived<TrezorCryptoResultRef>, Failure>(data)
                .map_err(|_| WireError::DecodeError)?;
            match archived {
                rkyv::Archived::<TrezorCryptoResultRef>::Xpub(xpub) => Ok(*xpub),
                _ => Err(WireError::UnexpectedResponse),
            }
        })()
        .into()
    }

    extern "C" fn get_public_key<'a>(
        &self,
        address_n: Slice<'a, u32>,
        compressed: bool,
    ) -> FastResult<BoxedSlice<u8>, WireError> {
        (|| {
            let data = ipc_crypto_call(&TrezorCryptoEnum::GetPublicKey {
                address_n: address_n.as_slice().into(),
                compressed,
            })?;
            let archived = rkyv::access::<rkyv::Archived<TrezorCryptoResultRef>, Failure>(data)
                .map_err(|_| WireError::DecodeError)?;
            match archived {
                rkyv::Archived::<TrezorCryptoResultRef>::PublicKey(key) => {
                    Ok(BoxedSlice::from(key.as_ref()))
                }
                _ => Err(WireError::UnexpectedResponse),
            }
        })()
        .into()
    }

    extern "C" fn sign_typed_hash<'a>(
        &self,
        address_n: Slice<'a, u32>,
        hash: [u8; 32],
        encoded_network: StabbyOption<Slice<'a, u8>>,
        encoded_token: StabbyOption<Slice<'a, u8>>,
        chain_id: StabbyOption<u64>,
        show_progress: bool,
    ) -> FastResult<[u8; 65], WireError> {
        (|| {
            let data = ipc_crypto_call(&TrezorCryptoEnum::SignTypedHash {
                address_n: address_n.as_slice().into(),
                hash,
                encoded_network: core::option::Option::from(encoded_network)
                    .map(|s: Slice<'a, u8>| s.as_slice().into()),
                encoded_token: core::option::Option::from(encoded_token)
                    .map(|s: Slice<'a, u8>| s.as_slice().into()),
                chain_id: chain_id.into(),
                show_progress,
            })?;
            let archived = rkyv::access::<rkyv::Archived<TrezorCryptoResultRef>, Failure>(data)
                .map_err(|_| WireError::DecodeError)?;
            match archived {
                rkyv::Archived::<TrezorCryptoResultRef>::Signature(sig) => Ok(*sig),
                _ => Err(WireError::UnexpectedResponse),
            }
        })()
        .into()
    }

    extern "C" fn sign_digest<'a>(
        &self,
        address_n: Slice<'a, u32>,
        digest: [u8; 32],
        compressed: bool,
    ) -> FastResult<[u8; 65], WireError> {
        (|| {
            let data = ipc_crypto_call(&TrezorCryptoEnum::SignDigest {
                address_n: address_n.as_slice().into(),
                digest,
                compressed,
            })?;
            let archived = rkyv::access::<rkyv::Archived<TrezorCryptoResultRef>, Failure>(data)
                .map_err(|_| WireError::DecodeError)?;
            match archived {
                rkyv::Archived::<TrezorCryptoResultRef>::Signature(sig) => Ok(*sig),
                _ => Err(WireError::UnexpectedResponse),
            }
        })()
        .into()
    }

    extern "C" fn check_address_mac<'a>(
        &self,
        address_n: Slice<'a, u32>,
        mac: [u8; 32],
        address: Str<'a>,
    ) -> FastResult<bool, WireError> {
        (|| {
            let data = ipc_crypto_call(&TrezorCryptoEnum::CheckAddressMac {
                address_n: address_n.as_slice().into(),
                mac,
                address: address.as_str().into(),
            })?;
            let archived = rkyv::access::<rkyv::Archived<TrezorCryptoResultRef>, Failure>(data)
                .map_err(|_| WireError::DecodeError)?;
            match archived {
                rkyv::Archived::<TrezorCryptoResultRef>::Boolean(valid) => Ok(*valid),
                _ => Err(WireError::UnexpectedResponse),
            }
        })()
        .into()
    }

    extern "C" fn get_address_mac<'a>(
        &self,
        address_n: Slice<'a, u32>,
        address: Str<'a>,
    ) -> FastResult<[u8; 32], WireError> {
        (|| {
            let data = ipc_crypto_call(&TrezorCryptoEnum::GetAddressMac {
                address_n: address_n.as_slice().into(),
                address: address.as_str().into(),
            })?;
            let archived = rkyv::access::<rkyv::Archived<TrezorCryptoResultRef>, Failure>(data)
                .map_err(|_| WireError::DecodeError)?;
            match archived {
                rkyv::Archived::<TrezorCryptoResultRef>::AddressMac(mac) => Ok(*mac),
                _ => Err(WireError::UnexpectedResponse),
            }
        })()
        .into()
    }

    extern "C" fn verify_nonce_cache<'a>(
        &self,
        nonce: Slice<'a, u8>,
    ) -> FastResult<bool, WireError> {
        (|| {
            let data = ipc_crypto_call(&TrezorCryptoEnum::VerifyNonceCache {
                nonce: nonce.as_slice().into(),
            })?;
            let archived = rkyv::access::<rkyv::Archived<TrezorCryptoResultRef>, Failure>(data)
                .map_err(|_| WireError::DecodeError)?;
            match archived {
                rkyv::Archived::<TrezorCryptoResultRef>::Boolean(valid) => Ok(*valid),
                _ => Err(WireError::UnexpectedResponse),
            }
        })()
        .into()
    }

    extern "C" fn ec_verify_recover<'a>(
        &self,
        curve: EcCurve,
        public_key: Slice<'a, u8>,
        signature: Slice<'a, u8>,
        message: Slice<'a, u8>,
    ) -> FastResult<BoxedSlice<u8>, CryptoError> {
        match curve {
            EcCurve::Secp256k1 | EcCurve::Nist256p1 => {
                let digest = sha256_digest(message.as_slice());
                ecdsa_verify_recover_digest(
                    curve,
                    public_key.as_slice(),
                    signature.as_slice(),
                    &digest,
                )
                .into()
            }
            EcCurve::Ed25519 => {
                let public_key: &crypto::ed25519::PublicKey = match public_key.as_slice().try_into()
                {
                    Ok(pk) => pk,
                    Err(_) => return Err(CryptoError::InvalidEncoding).into(),
                };
                let signature: &crypto::ed25519::Signature = match signature.as_slice().try_into() {
                    Ok(sig) => sig,
                    Err(_) => return Err(CryptoError::InvalidEncoding).into(),
                };
                match crypto::ed25519::verify(message.as_slice(), public_key, signature) {
                    Ok(()) => Ok(BoxedSlice::from(&public_key[..])).into(),
                    Err(_) => Err(CryptoError::InvalidSignature).into(),
                }
            }
        }
    }

    extern "C" fn ec_verify_recover_digest<'a>(
        &self,
        curve: EcCurve,
        public_key: Slice<'a, u8>,
        signature: Slice<'a, u8>,
        digest: Slice<'a, u8>,
    ) -> FastResult<BoxedSlice<u8>, CryptoError> {
        match curve {
            EcCurve::Secp256k1 | EcCurve::Nist256p1 => ecdsa_verify_recover_digest(
                curve,
                public_key.as_slice(),
                signature.as_slice(),
                digest.as_slice(),
            )
            .into(),
            // EdDSA has no notion of signing/verifying a pre-hashed digest —
            // it always hashes the message itself as part of the scheme.
            EcCurve::Ed25519 => Err(CryptoError::InvalidSignature).into(),
        }
    }

    extern "C" fn base58_encode<'a>(&self, data: Slice<'a, u8>) -> String {
        String::from(bs58::encode(data.as_slice()).into_string().as_str())
    }

    extern "C" fn base58_decode<'a>(
        &self,
        data: Str<'a>,
    ) -> FastResult<BoxedSlice<u8>, CryptoError> {
        match bs58::decode(data.as_str()).into_vec() {
            Ok(bytes) => Ok(BoxedSlice::from(&bytes[..])).into(),
            Err(_) => Err(CryptoError::InvalidEncoding).into(),
        }
    }

    extern "C" fn base58check_encode<'a>(&self, data: Slice<'a, u8>) -> String {
        String::from(
            bs58::encode(data.as_slice())
                .with_check()
                .into_string()
                .as_str(),
        )
    }

    extern "C" fn base58check_decode<'a>(
        &self,
        data: Str<'a>,
    ) -> FastResult<BoxedSlice<u8>, CryptoError> {
        match bs58::decode(data.as_str()).with_check(None).into_vec() {
            Ok(bytes) => Ok(BoxedSlice::from(&bytes[..])).into(),
            Err(_) => Err(CryptoError::InvalidEncoding).into(),
        }
    }
}

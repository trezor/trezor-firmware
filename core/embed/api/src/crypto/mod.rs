use alloc::vec::Vec;

use rkyv::rancor::Failure;
use stabby::boxed::BoxedSlice;
use stabby::slice::Slice;
use stabby::str::Str;
use stabby::string::String;
use trezor_app_sdk::structs::{TrezorCryptoEnum, TrezorCryptoResult};
use trezor_app_sdk::traits::crypto::{
    BoxedHasher, CanonicalSig, CryptoError, CryptoV1, EcCurve, HashingAlgorithm, HmacAlgorithm,
};
use trezor_app_sdk::traits::util::{FastResult, TIMEOUT_MAX};
use trezor_app_sdk::traits::wire::WireError;

use crate::wire::{CoreIpcService, ipc_call, to_bytes};

mod hashers;

/// Serializes `value` and sends it to Core's crypto service, returning the
/// raw response bytes. Each `CryptoV1` method reads the [`TrezorCryptoResult`]
/// shape it expects out of them with one of the `expect_*` helpers below, and
/// copies out its own return value before the buffer goes out of scope.
fn ipc_crypto_call(value: &TrezorCryptoEnum) -> Result<BoxedSlice<u8>, WireError> {
    let bytes = to_bytes(value).map_err(|_| WireError::DecodeError)?;
    let (_id, data) = ipc_call(
        CoreIpcService::Crypto.into(),
        value.id() as u16,
        &bytes,
        TIMEOUT_MAX,
    )?;
    Ok(data)
}

/// The archived [`TrezorCryptoResult`] in a crypto service response.
fn access_result(data: &[u8]) -> Result<&rkyv::Archived<TrezorCryptoResult<'_>>, WireError> {
    rkyv::access::<rkyv::Archived<TrezorCryptoResult>, Failure>(data)
        .map_err(|_| WireError::DecodeError)
}

/// A `Bytes` result.
fn expect_bytes(data: &[u8]) -> Result<&[u8], WireError> {
    match access_result(data)? {
        rkyv::Archived::<TrezorCryptoResult>::Bytes(bytes) => Ok(bytes.as_ref()),
        _ => Err(WireError::UnexpectedResponse),
    }
}

/// A `Bytes` result of exactly `N` bytes.
fn expect_array<const N: usize>(data: &[u8]) -> Result<[u8; N], WireError> {
    expect_bytes(data)?
        .try_into()
        .map_err(|_| WireError::UnexpectedResponse)
}

/// A `String` result.
fn expect_str(data: &[u8]) -> Result<&str, WireError> {
    match access_result(data)? {
        rkyv::Archived::<TrezorCryptoResult>::String(string) => Ok(string.as_ref()),
        _ => Err(WireError::UnexpectedResponse),
    }
}

/// A `Boolean` result.
fn expect_bool(data: &[u8]) -> Result<bool, WireError> {
    match access_result(data)? {
        rkyv::Archived::<TrezorCryptoResult>::Boolean(value) => Ok(*value),
        _ => Err(WireError::UnexpectedResponse),
    }
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
        if let Ok(recovered) = crypto::ecdsa::verify_recover(
            curve,
            signature,
            crypto::ecdsa::RecId::new(recid),
            digest,
        ) {
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
            HashingAlgorithm::Sha3_512 => hashers::Sha3::new(512, false).into(),
            HashingAlgorithm::Keccak512 => hashers::Sha3::new(512, true).into(),
        }
    }

    extern "C" fn get_hmac<'a>(&self, algorithm: HmacAlgorithm, key: Slice<'a, u8>) -> BoxedHasher {
        match algorithm {
            HmacAlgorithm::Sha256 => hashers::HmacSha256::new(key.as_slice()).into(),
            HmacAlgorithm::Sha512 => hashers::HmacSha512::new(key.as_slice()).into(),
        }
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
            expect_str(&data)?
                .as_bytes()
                .try_into()
                .map_err(|_| WireError::UnexpectedResponse)
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
            let key = expect_bytes(&data)?;
            match key.len() {
                32 | 33 | 65 => Ok(BoxedSlice::from(key)),
                _ => Err(WireError::UnexpectedResponse),
            }
        })()
        .into()
    }

    extern "C" fn sign_digest<'a>(
        &self,
        address_n: Slice<'a, u32>,
        digest: &'a [u8; 32],
        compressed: bool,
        canonical: CanonicalSig,
    ) -> FastResult<[u8; 65], WireError> {
        (|| {
            let data = ipc_crypto_call(&TrezorCryptoEnum::SignDigest {
                address_n: address_n.as_slice().into(),
                digest: *digest,
                compressed,
                canonical: canonical as u8,
            })?;
            expect_array::<65>(&data)
        })()
        .into()
    }

    extern "C" fn check_address_mac<'a>(
        &self,
        address_n: Slice<'a, u32>,
        mac: &'a [u8; 32],
        address: Str<'a>,
        slip44: u32,
    ) -> FastResult<bool, WireError> {
        (|| {
            let data = ipc_crypto_call(&TrezorCryptoEnum::CheckAddressMac {
                address_n: address_n.as_slice().into(),
                mac: *mac,
                address: address.as_str().into(),
                slip44,
            })?;
            expect_bool(&data)
        })()
        .into()
    }

    extern "C" fn get_address_mac<'a>(
        &self,
        address_n: Slice<'a, u32>,
        address: Str<'a>,
        slip44: u32,
    ) -> FastResult<[u8; 32], WireError> {
        (|| {
            let data = ipc_crypto_call(&TrezorCryptoEnum::GetAddressMac {
                address_n: address_n.as_slice().into(),
                address: address.as_str().into(),
                slip44,
            })?;
            expect_array::<32>(&data)
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
            expect_bool(&data)
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

    extern "C" fn ec_recover_pubkey<'a>(
        &self,
        curve: EcCurve,
        signature: Slice<'a, u8>,
        digest: Slice<'a, u8>,
    ) -> FastResult<BoxedSlice<u8>, CryptoError> {
        (|| {
            let Some(curve) = ecdsa_curve(curve) else {
                return Err(CryptoError::InvalidSignature);
            };
            let (recid_byte, rs) = signature
                .as_slice()
                .split_first()
                .ok_or(CryptoError::InvalidEncoding)?;
            let recid = crypto::ecdsa::RecId::try_new(*recid_byte)
                .map_err(|_| CryptoError::InvalidEncoding)?;
            let rs: &crypto::ecdsa::EcdsaSignature =
                rs.try_into().map_err(|_| CryptoError::InvalidEncoding)?;
            let digest: &crypto::ecdsa::EcdsaDigest = digest
                .as_slice()
                .try_into()
                .map_err(|_| CryptoError::InvalidEncoding)?;
            let pubkey = crypto::ecdsa::verify_recover(curve, rs, recid, digest)
                .map_err(|_| CryptoError::InvalidSignature)?;
            Ok(BoxedSlice::from(&pubkey[..]))
        })()
        .into()
    }

    extern "C" fn cosi_verify<'a>(
        &self,
        threshold: u8,
        message: Slice<'a, u8>,
        public_keys: Slice<'a, [u8; 32]>,
        sigmask: u8,
        signature: Slice<'a, u8>,
    ) -> FastResult<(), CryptoError> {
        (|| {
            let sig: &crypto::ed25519::Signature = signature
                .as_slice()
                .try_into()
                .map_err(|_| CryptoError::InvalidEncoding)?;
            let cosi_sig = crypto::cosi::Signature::new(sigmask, *sig);

            let keys: Result<Vec<crypto::ed25519::PublicKey>, CryptoError> = public_keys
                .as_slice()
                .iter()
                .map(|k| {
                    let key: &crypto::ed25519::PublicKey =
                        k[..].try_into().map_err(|_| CryptoError::InvalidEncoding)?;
                    Ok(*key)
                })
                .collect();
            let keys = keys?;

            crypto::cosi::verify(threshold, message.as_slice(), &keys, &cosi_sig)
                .map_err(|_| CryptoError::InvalidSignature)?;
            Ok(())
        })()
        .into()
    }

    extern "C" fn cosi_combine_publickeys<'a>(
        &self,
        public_keys: Slice<'a, [u8; 32]>,
    ) -> FastResult<[u8; 32], CryptoError> {
        (|| {
            let keys: Vec<crypto::ed25519::PublicKey> = public_keys
                .as_slice()
                .iter()
                .map(|k| {
                    let key: &crypto::ed25519::PublicKey =
                        k[..].try_into().map_err(|_| CryptoError::InvalidEncoding)?;
                    Ok(*key)
                })
                .collect::<Result<_, CryptoError>>()?;

            crypto::cosi::combine_publickeys(&keys).map_err(|_| CryptoError::InvalidEncoding)
        })()
        .into()
    }

    extern "C" fn base58_encode<'a>(&self, data: Slice<'a, u8>) -> FastResult<String, CryptoError> {
        let mut buffer = alloc::vec![0u8; crypto::base58::encoded_len_max(data.len())];
        crypto::base58::encode_str(data.as_slice(), &mut buffer)
            .map(String::from)
            .map_err(|_| CryptoError::InvalidEncoding)
            .into()
    }

    extern "C" fn base58_decode<'a>(
        &self,
        data: Str<'a>,
    ) -> FastResult<BoxedSlice<u8>, CryptoError> {
        let mut buffer = alloc::vec![0u8; crypto::base58::decoded_len_max(data.as_str())];
        crypto::base58::decode(data.as_str(), &mut buffer)
            .map(|len| BoxedSlice::from(&buffer[..len]))
            .map_err(|_| CryptoError::InvalidEncoding)
            .into()
    }

    extern "C" fn base58check_encode<'a>(
        &self,
        data: Slice<'a, u8>,
    ) -> FastResult<String, CryptoError> {
        let encoded_len =
            crypto::base58::encoded_len_max(data.len() + crypto::base58::CHECKSUM_LEN);
        let mut buffer = alloc::vec![0u8; encoded_len];
        crypto::base58::encode_check_str(data.as_slice(), &mut buffer)
            .map(String::from)
            .map_err(|_| CryptoError::InvalidEncoding)
            .into()
    }

    extern "C" fn base58check_decode<'a>(
        &self,
        data: Str<'a>,
    ) -> FastResult<BoxedSlice<u8>, CryptoError> {
        // Also holds the checksum, which `decoded_len_max` accounts for.
        let mut buffer = alloc::vec![0u8; crypto::base58::decoded_len_max(data.as_str())];
        crypto::base58::decode_check(data.as_str(), &mut buffer)
            .map(|len| BoxedSlice::from(&buffer[..len]))
            .map_err(|_| CryptoError::InvalidEncoding)
            .into()
    }
}

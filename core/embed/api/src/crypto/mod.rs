use stabby::boxed::{Box, BoxedSlice};
use stabby::slice::Slice;
use stabby::str::Str;
use stabby::string::String;
use trezor_app_sdk::traits::crypto::{
    BoxedHasher, CryptoError, CryptoV1, EcCurve, HashingAlgorithm,
};
use trezor_app_sdk::traits::util::FastResult;

mod hashers;

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
        }
    }

    extern "C" fn get_hmac_hasher<'a>(&self, key: Slice<'a, u8>) -> BoxedHasher {
        let hasher = hashers::HmacSha256::new(key.as_slice());
        hasher.into()
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

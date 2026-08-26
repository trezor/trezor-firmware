use alloc::boxed::Box;

use stabby::boxed::BoxedSlice;
use stabby::slice::Slice;
use stabby::str::Str;
use stabby::string::String;
use trezor_app_sdk::traits::crypto::{
    BoxedHasher, CryptoError, CryptoV1, EcCurve, HashingAlgorithm,
};
use trezor_app_sdk::traits::util::FastResult;

/// The actual state behind a [`BoxedHasher`] handle. Each hasher gets its
/// own heap allocation (see [`box_hasher`]), pinned at that address for its
/// lifetime — as opposed to a fixed slot per algorithm — so any number of
/// hashers, of any mix of algorithms, can be in flight at once.
enum HasherState {
    Sha256(crypto::sha256::Sha256<Box<crypto::sha256::Sha256Ctx>>),
    Sha512(crypto::sha512::Sha512<Box<crypto::sha512::Sha512Ctx>>),
    Sha3_256(crypto::sha3::Sha3_256<Box<crypto::sha3::Sha3Ctx>>),
    Keccak256(crypto::sha3::Keccak256<Box<crypto::sha3::Sha3Ctx>>),
    HmacSha256(crypto::hmac::HmacSha256<Box<crypto::hmac::HmacSha256Ctx>>),
}

/// Heap-allocates `state` and mints an opaque handle to it for the app.
fn box_hasher(state: HasherState) -> BoxedHasher {
    BoxedHasher(Box::into_raw(Box::new(state)).cast())
}

/// Borrows the hasher state behind a handle minted by [`box_hasher`], without
/// taking ownership — for `hasher_update`, which may be called any number of
/// times before the handle is finalized.
///
/// # Safety
///
/// `hasher` must be a handle minted by [`box_hasher`] that has not yet been
/// passed to [`hasher_into_owned`].
unsafe fn hasher_from_handle<'a>(hasher: BoxedHasher) -> &'a mut HasherState {
    // SAFETY: caller's responsibility, see above.
    unsafe { &mut *hasher.0.cast::<HasherState>() }
}

/// Reclaims ownership of the hasher state behind a handle minted by
/// [`box_hasher`] — for `hasher_finalize`, which consumes the handle exactly
/// once, freeing the allocation when the returned value is dropped.
///
/// # Safety
///
/// `hasher` must be a handle minted by [`box_hasher`], not already passed to
/// this function.
unsafe fn hasher_into_owned(hasher: BoxedHasher) -> HasherState {
    // SAFETY: caller's responsibility, see above.
    unsafe { *Box::from_raw(hasher.0.cast::<HasherState>()) }
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
        let state = match algorithm {
            HashingAlgorithm::Sha256 => HasherState::Sha256(crypto::sha256::Sha256::new(
                Box::new(crypto::sha256::Sha256Ctx::default()),
            )),
            HashingAlgorithm::Sha512 => HasherState::Sha512(crypto::sha512::Sha512::new(
                Box::new(crypto::sha512::Sha512Ctx::default()),
            )),
            HashingAlgorithm::Sha3_256 => HasherState::Sha3_256(crypto::sha3::Sha3_256::new(
                Box::new(crypto::sha3::Sha3Ctx::default()),
            )),
            HashingAlgorithm::Keccak256 => HasherState::Keccak256(crypto::sha3::Keccak256::new(
                Box::new(crypto::sha3::Sha3Ctx::default()),
            )),
        };
        box_hasher(state)
    }

    extern "C" fn get_hmac_hasher<'a>(&self, key: Slice<'a, u8>) -> BoxedHasher {
        let state = HasherState::HmacSha256(crypto::hmac::HmacSha256::new(
            Box::new(crypto::hmac::HmacSha256Ctx::default()),
            key.as_slice(),
        ));
        box_hasher(state)
    }

    extern "C" fn hasher_update<'a>(&self, hasher: BoxedHasher, input: Slice<'a, u8>) {
        // SAFETY: `hasher` is a handle the app got from `get_hasher` /
        // `get_hmac_hasher` and has not yet finalized.
        let state = unsafe { hasher_from_handle(hasher) };
        let data = input.as_slice();
        match state {
            HasherState::Sha256(h) => h.update(data),
            HasherState::Sha512(h) => h.update(data),
            HasherState::Sha3_256(h) => h.update(data),
            HasherState::Keccak256(h) => h.update(data),
            HasherState::HmacSha256(h) => h.update(data),
        }
    }

    extern "C" fn hasher_finalize(&self, hasher: BoxedHasher) -> BoxedSlice<u8> {
        // SAFETY: `hasher` is a handle the app got from `get_hasher` /
        // `get_hmac_hasher`, finalized here exactly once.
        let state = unsafe { hasher_into_owned(hasher) };
        match state {
            HasherState::Sha256(h) => BoxedSlice::from(&h.finalize()[..]),
            HasherState::Sha512(h) => BoxedSlice::from(&h.finalize()[..]),
            HasherState::Sha3_256(h) => BoxedSlice::from(&h.finalize()[..]),
            HasherState::Keccak256(h) => BoxedSlice::from(&h.finalize()[..]),
            HasherState::HmacSha256(h) => BoxedSlice::from(&h.finalize()[..]),
        }
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

use rkyv::rancor::Failure;
use rtl::unwrap;
use stabby::boxed::BoxedSlice;
use stabby::slice::Slice;
use stabby::str::Str;
use stabby::string::String;
use trezor_app_sdk::structs::{TrezorCryptoEnum, TrezorCryptoResult};
use trezor_app_sdk::traits::crypto::{
    BoxedHasher, CanonicalSig, CryptoError, CryptoV1, Curve, EcdsaCurve, HashingAlgorithm,
    HmacAlgorithm, XPUB_RAW_LEN,
};
use trezor_app_sdk::traits::util::{CoreServiceError, FastResult, ServiceResult, TIMEOUT_MAX};

use crate::wire::{CoreIpcService, MSG_ID_ERROR, call_failed, ipc_call, service_error, to_bytes};

/// A failed call into Core's crypto service, as reported to the app.
type CryptoCallError = CoreServiceError<CryptoError>;

fn unexpected_response() -> CryptoCallError {
    call_failed("unexpected crypto response")
}

mod hashers;

/// Serializes `value` and sends it to Core's crypto service, returning the
/// raw response bytes. Each `CryptoV1` method reads the [`TrezorCryptoResult`]
/// shape it expects out of them with one of the `expect_*` helpers below, and
/// copies out its own return value before the buffer goes out of scope.
fn ipc_crypto_call(value: &TrezorCryptoEnum) -> Result<BoxedSlice<u8>, CryptoCallError> {
    let bytes = to_bytes(value).map_err(|_| call_failed("failed to serialize crypto request"))?;
    let id = value.id() as u16;
    let (response_id, data) =
        ipc_call(CoreIpcService::Crypto.into(), id, &bytes, TIMEOUT_MAX).map_err(service_error)?;
    if response_id == MSG_ID_ERROR {
        // Core has logged why
        return Err(CoreServiceError::ServiceCallFailed);
    }
    // Core answers with the id of the request
    if response_id != id {
        return Err(unexpected_response());
    }
    Ok(data)
}

/// The archived [`TrezorCryptoResult`] in a crypto service response.
fn access_result(data: &[u8]) -> Result<&rkyv::Archived<TrezorCryptoResult<'_>>, CryptoCallError> {
    rkyv::access::<rkyv::Archived<TrezorCryptoResult>, Failure>(data)
        .map_err(|_| call_failed("failed to decode crypto response"))
}

/// A `Bytes` result.
fn expect_bytes(data: &[u8]) -> Result<&[u8], CryptoCallError> {
    match access_result(data)? {
        rkyv::Archived::<TrezorCryptoResult>::Bytes(bytes) => Ok(bytes.as_ref()),
        _ => Err(unexpected_response()),
    }
}

/// A `Bytes` result of exactly `N` bytes.
fn expect_array<const N: usize>(data: &[u8]) -> Result<[u8; N], CryptoCallError> {
    expect_bytes(data)?
        .try_into()
        .map_err(|_| unexpected_response())
}

/// A `Boolean` result.
fn expect_bool(data: &[u8]) -> Result<bool, CryptoCallError> {
    match access_result(data)? {
        rkyv::Archived::<TrezorCryptoResult>::Boolean(value) => Ok(*value),
        _ => Err(unexpected_response()),
    }
}

/// Maps an [`EcdsaCurve`] to the curve `crypto::ecdsa` understands.
fn ecdsa_curve(curve: EcdsaCurve) -> crypto::ecdsa::Curve {
    match curve {
        EcdsaCurve::Secp256k1 => crypto::ecdsa::Curve::Secp256k1,
        EcdsaCurve::Nist256p1 => crypto::ecdsa::Curve::Nist256p1,
    }
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

/// Verifies `signature` of `digest` by trying every ECDSA recovery id and
/// checking whether any recovered pubkey matches `public_key`.
fn ecdsa_verify_by_recovery(
    curve: EcdsaCurve,
    public_key: &[u8],
    signature: &[u8],
    digest: &[u8],
) -> Result<(), CryptoError> {
    // compressed (0x02/0x03) or uncompressed (0x04) SEC1 key
    match public_key.first() {
        Some(0x02 | 0x03)
            if public_key.len() == crypto::ecdsa::ECDSA_PUBLIC_KEY_COMPRESSED_SIZE => {}
        Some(0x04) if public_key.len() == crypto::ecdsa::ECDSA_PUBLIC_KEY_SIZE => {}
        _ => return Err(CryptoError::InvalidEncoding),
    }
    let curve = ecdsa_curve(curve);
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
        ) && pubkey_matches(&recovered, public_key)
        {
            return Ok(());
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
        curve: Curve,
        address_n: Slice<'a, u32>,
    ) -> ServiceResult<[u8; XPUB_RAW_LEN], CryptoError> {
        (|| {
            let data = ipc_crypto_call(&TrezorCryptoEnum::GetXpub {
                curve: curve as u8,
                address_n: address_n.as_slice().into(),
            })?;
            expect_array::<XPUB_RAW_LEN>(&data)
        })()
        .into()
    }

    extern "C" fn get_public_key<'a>(
        &self,
        curve: Curve,
        address_n: Slice<'a, u32>,
        compressed: bool,
    ) -> ServiceResult<BoxedSlice<u8>, CryptoError> {
        (|| {
            let data = ipc_crypto_call(&TrezorCryptoEnum::GetPublicKey {
                curve: curve as u8,
                address_n: address_n.as_slice().into(),
                compressed,
            })?;
            let key = expect_bytes(&data)?;
            match key.len() {
                32 | 33 | 65 => Ok(BoxedSlice::from(key)),
                _ => Err(unexpected_response()),
            }
        })()
        .into()
    }

    extern "C" fn ecdsa_sign_digest<'a>(
        &self,
        curve: EcdsaCurve,
        address_n: Slice<'a, u32>,
        digest: &'a [u8; 32],
        compressed: bool,
        canonical: CanonicalSig,
    ) -> ServiceResult<[u8; 65], CryptoError> {
        (|| {
            let data = ipc_crypto_call(&TrezorCryptoEnum::EcdsaSignDigest {
                curve: curve as u8,
                address_n: address_n.as_slice().into(),
                digest: *digest,
                compressed,
                canonical: canonical as u8,
            })?;
            expect_array::<65>(&data)
        })()
        .into()
    }

    extern "C" fn ed25519_sign<'a>(
        &self,
        address_n: Slice<'a, u32>,
        message: Slice<'a, u8>,
    ) -> ServiceResult<[u8; 64], CryptoError> {
        (|| {
            let data = ipc_crypto_call(&TrezorCryptoEnum::Ed25519Sign {
                address_n: address_n.as_slice().into(),
                message: message.as_slice().into(),
            })?;
            expect_array::<64>(&data)
        })()
        .into()
    }

    extern "C" fn check_address_mac<'a>(
        &self,
        address_n: Slice<'a, u32>,
        mac: &'a [u8; 32],
        address: Str<'a>,
        slip44: u32,
    ) -> ServiceResult<(), CryptoError> {
        (|| {
            let data = ipc_crypto_call(&TrezorCryptoEnum::CheckAddressMac {
                address_n: address_n.as_slice().into(),
                mac: *mac,
                address: address.as_str().into(),
                slip44,
            })?;
            match expect_bool(&data)? {
                true => Ok(()),
                // a wrong MAC comes back as `MSG_ID_ERROR`
                false => Err(CoreServiceError::ServiceCallFailed),
            }
        })()
        .into()
    }

    extern "C" fn get_address_mac<'a>(
        &self,
        address_n: Slice<'a, u32>,
        address: Str<'a>,
        slip44: u32,
    ) -> ServiceResult<[u8; 32], CryptoError> {
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

    extern "C" fn ecdsa_verify_digest<'a>(
        &self,
        curve: EcdsaCurve,
        public_key: Slice<'a, u8>,
        signature: Slice<'a, u8>,
        digest: Slice<'a, u8>,
    ) -> FastResult<(), CryptoError> {
        ecdsa_verify_by_recovery(
            curve,
            public_key.as_slice(),
            signature.as_slice(),
            digest.as_slice(),
        )
        .into()
    }

    extern "C" fn ecdsa_recover_pubkey<'a>(
        &self,
        curve: EcdsaCurve,
        signature: Slice<'a, u8>,
        digest: Slice<'a, u8>,
    ) -> FastResult<BoxedSlice<u8>, CryptoError> {
        (|| {
            let curve = ecdsa_curve(curve);
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

    extern "C" fn ed25519_verify<'a>(
        &self,
        public_key: Slice<'a, u8>,
        signature: Slice<'a, u8>,
        message: Slice<'a, u8>,
    ) -> FastResult<(), CryptoError> {
        (|| {
            let public_key: &crypto::ed25519::PublicKey = public_key
                .as_slice()
                .try_into()
                .map_err(|_| CryptoError::InvalidPublicKey)?;
            let signature: &crypto::ed25519::Signature = signature
                .as_slice()
                .try_into()
                .map_err(|_| CryptoError::InvalidEncoding)?;
            crypto::ed25519::verify(message.as_slice(), public_key, signature)
                .map_err(|_| CryptoError::InvalidSignature)
        })()
        .into()
    }

    extern "C" fn base58_encode<'a>(&self, data: Slice<'a, u8>) -> String {
        let mut buffer = alloc::vec![0u8; crypto::base58::encoded_len_max(data.len())];
        // Can't fail: only a short buffer is an error, `encoded_len_max` never is.
        String::from(unwrap!(crypto::base58::encode_str(
            data.as_slice(),
            &mut buffer
        )))
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

    extern "C" fn base58check_encode<'a>(&self, data: Slice<'a, u8>) -> String {
        let encoded_len =
            crypto::base58::encoded_len_max(data.len() + crypto::base58::CHECKSUM_LEN);
        let mut buffer = alloc::vec![0u8; encoded_len];
        // Can't fail: only a short buffer is an error, `encoded_len_max` never is.
        String::from(unwrap!(crypto::base58::encode_check_str(
            data.as_slice(),
            &mut buffer
        )))
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

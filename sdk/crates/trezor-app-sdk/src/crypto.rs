//! High-level crypto API
//!
//! This module provides user-friendly functions for interacting with the Trezor crypto.

pub use rkyv::Archived;
use rkyv::rancor::Failure;
use rkyv::to_bytes;

use crate::alloc_types::Vec;
use crate::core_services::services_or_die;
use crate::ipc::IpcMessage;
pub use crate::low_level_api::ffi::{HMAC_SHA256_CTX, SHA256_CTX, SHA512_CTX};
use crate::low_level_api::{ed25519_cosi_combine_publickeys, ed25519_sign_open, get_crypto_or_die};
use crate::service::CoreIpcService;
use crate::structs::TrezorCryptoResultRef;
pub use crate::structs::{TrezorCryptoEnum, TrezorCryptoResult};
use crate::util::Timeout;
use crate::{Error, Result, unwrap};

// ============================================================================
// Helper Functions
// ============================================================================

type CryptoResult = Result<TrezorCryptoResult>;

fn ipc_crypto_call<'a>(value: &TrezorCryptoEnum<'a>) -> CryptoResult {
    let bytes = unwrap!(to_bytes::<Failure>(value));

    let message = IpcMessage::new(value.id() as _, bytes.as_ref());
    let result = services_or_die().call(CoreIpcService::Crypto, &message, Timeout::max())?;

    // Safe validation using bytecheck before accessing archived data
    let archived = unwrap!(rkyv::access::<Archived<TrezorCryptoResultRef>, Failure>(
        result.data()
    ));

    let result = match archived {
        Archived::<TrezorCryptoResultRef>::AddressMac(mac) => TrezorCryptoResult::AddressMac(*mac),
        Archived::<TrezorCryptoResultRef>::Boolean(valid) => TrezorCryptoResult::Boolean(*valid),
        Archived::<TrezorCryptoResultRef>::Xpub(xpub) => TrezorCryptoResult::Xpub(*xpub),
        Archived::<TrezorCryptoResultRef>::PublicKey(xpub) => {
            TrezorCryptoResult::PublicKey(Vec::from(xpub.as_ref()))
        }
        Archived::<TrezorCryptoResultRef>::Signature(signature) => {
            TrezorCryptoResult::Signature(*signature)
        }
    };

    Ok(result)
}

fn ecdsa_verify_digest(
    curve: *const crate::low_level_api::ffi::ecdsa_curve,
    public_key: &[u8],
    signature: &[u8],
    digest: &[u8; 32],
) -> bool {
    if public_key.len() != 33 && public_key.len() != 65 {
        return false;
    }
    if signature.len() != 64 && signature.len() != 65 {
        return false;
    }
    let offset = signature.len() - 64;
    unsafe {
        unwrap!(get_crypto_or_die().ecdsa_verify_digest)(
            &*curve,
            public_key.as_ptr(),
            &signature[offset],
            digest.as_ptr(),
        ) == 0
    }
}

fn ecdsa_recover(
    curve: *const crate::low_level_api::ffi::ecdsa_curve,
    signature: &[u8; 65],
    digest: &[u8; 32],
) -> Option<crate::alloc_types::Vec<u8>> {
    let mut recid = signature[0] - 27;
    if recid >= 8 {
        return None;
    }
    let compressed = recid >= 4;
    recid &= 3;
    let mut pub_key = [0u8; 65];

    if unsafe {
        unwrap!(get_crypto_or_die().ecdsa_recover_pub_from_sig)(
            &*curve,
            &mut pub_key as *mut u8,
            &signature[1],
            digest.as_ptr(),
            recid.into(),
        )
    } != 0
    {
        return None;
    }

    if compressed {
        pub_key[0] = 0x02 | (pub_key[64] & 1);
    }

    let len = if compressed { 33 } else { 65 };
    let mut result = crate::alloc_types::Vec::with_capacity(len);
    result.extend_from_slice(&pub_key[..len]);
    Some(result)
}

// ============================================================================
// Public crypto Functions
// ============================================================================

/// A streaming hash function: feed input via [`update`](Hasher::update), read
/// the digest via [`finalize`](Hasher::finalize).
pub trait Hasher {
    /// Feeds more input into the hash state.
    fn update(&mut self, input: &[u8]);
    /// Writes the final digest into `output`, consuming accumulated state.
    fn finalize(&mut self, output: &mut [u8]);
}

/// Derives the extended public key (xpub) for `address_n`, tagged with the
/// given `xpub_magic` version bytes.
pub fn get_xpub(address_n: &[u32], xpub_magic: u32) -> Result<crate::alloc_types::String> {
    let value = TrezorCryptoEnum::GetXpub {
        address_n: address_n.into(),
        xpub_magic,
    };

    let res = ipc_crypto_call(&value);
    if let Ok(TrezorCryptoResult::Xpub(xpub)) = res {
        Ok(unwrap!(core::str::from_utf8(xpub.as_slice())).into())
    } else {
        // TODO: proper error type
        Err(Error::ApiError(crate::low_level_api::ApiError::Failed))?
    }
}

/// Derives the raw public key for `address_n`, in compressed or uncompressed form.
pub fn get_public_key(address_n: &[u32], compressed: bool) -> Result<crate::alloc_types::Vec<u8>> {
    let value = TrezorCryptoEnum::GetPublicKey {
        address_n: address_n.into(),
        compressed,
    };

    let res = ipc_crypto_call(&value);
    if let Ok(TrezorCryptoResult::PublicKey(xpub)) = res {
        Ok(xpub)
    } else {
        // TODO: proper error type
        Err(Error::ApiError(crate::low_level_api::ApiError::Failed))?
    }
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
    let value = TrezorCryptoEnum::SignTypedHash {
        address_n: address_n.into(),
        hash: *hash,
        encoded_network: encoded_network.map(|network| network.into()),
        encoded_token: encoded_token.map(|token| token.into()),
        chain_id,
        show_progress,
    };

    let res = ipc_crypto_call(&value);

    if let Ok(TrezorCryptoResult::Signature(signature)) = res {
        Ok(signature)
    } else {
        // TODO: proper error type
        Err(Error::ApiError(crate::low_level_api::ApiError::Failed))?
    }
}

/// Signs a raw 32-byte digest with the key at `address_n`.
pub fn sign_digest(address_n: &[u32], digest: &[u8; 32], compressed: bool) -> Result<[u8; 65]> {
    let value = TrezorCryptoEnum::SignDigest {
        address_n: address_n.into(),
        digest: *digest,
        compressed,
    };

    let res = ipc_crypto_call(&value);

    if let Ok(TrezorCryptoResult::Signature(signature)) = res {
        Ok(signature)
    } else {
        // TODO: proper error type
        Err(Error::ApiError(crate::low_level_api::ApiError::Failed))?
    }
}

/// Verifies a MAC previously produced by [`get_address_mac`] for `address_n`
/// and `address`, confirming the pairing hasn't been tampered with.
pub fn check_address_mac(address_n: &[u32], mac: &[u8; 32], address: &str) -> Result<bool> {
    let value = TrezorCryptoEnum::CheckAddressMac {
        address_n: address_n.into(),
        mac: *mac,
        address: address.into(),
    };

    let res = ipc_crypto_call(&value);

    if let Ok(TrezorCryptoResult::Boolean(valid)) = res {
        Ok(valid)
    } else {
        // TODO: proper error type
        Err(Error::ApiError(crate::low_level_api::ApiError::Failed))?
    }
}

/// Computes a MAC binding `address_n` to `address`, so a cached `address` can
/// later be re-authenticated via [`check_address_mac`] without a full re-derivation.
pub fn get_address_mac(address_n: &[u32], address: &str) -> Result<[u8; 32]> {
    let value = TrezorCryptoEnum::GetAddressMac {
        address_n: address_n.into(),
        address: address.into(),
    };

    let res = ipc_crypto_call(&value);

    if let Ok(TrezorCryptoResult::AddressMac(mac)) = res {
        Ok(mac)
    } else {
        // TODO: proper error type
        Err(Error::ApiError(crate::low_level_api::ApiError::Failed))?
    }
}

/// Checks `nonce` against Core's cached-nonce store, returning whether it's still valid.
pub fn verify_nonce_cache(nonce: &[u8]) -> Result<bool> {
    let value = TrezorCryptoEnum::VerifyNonceCache {
        nonce: nonce.into(),
    };

    let res = ipc_crypto_call(&value);

    if let Ok(TrezorCryptoResult::Boolean(valid)) = res {
        Ok(valid)
    } else {
        // TODO: proper error type
        Err(Error::ApiError(crate::low_level_api::ApiError::Failed))?
    }
}

/// ECDSA over the secp256k1 curve.
pub mod secp256k1 {
    use super::*;

    /// Verifies an ECDSA `signature` over `digest` against `public_key`.
    pub fn verify(public_key: &[u8], signature: &[u8], digest: &[u8; 32]) -> bool {
        ecdsa_verify_digest(get_crypto_or_die().secp256k1, public_key, signature, digest)
    }

    /// Recovers the public key that produced `signature` over `digest`, if any.
    pub fn verify_recover(
        signature: &[u8; 65],
        digest: &[u8; 32],
    ) -> Option<crate::alloc_types::Vec<u8>> {
        ecdsa_recover(get_crypto_or_die().secp256k1, signature, digest)
    }
}

/// ECDSA over the NIST P-256 (secp256r1) curve.
pub mod nist256p1 {
    use super::*;

    /// Verifies an ECDSA `signature` over `digest` against `public_key`.
    pub fn verify(public_key: &[u8], signature: &[u8], digest: &[u8; 32]) -> bool {
        ecdsa_verify_digest(get_crypto_or_die().nist256p1, public_key, signature, digest)
    }

    /// Recovers the public key that produced `signature` over `digest`, if any.
    pub fn verify_recover(signature: &[u8; 65], digest: &[u8; 32]) -> Option<Vec<u8>> {
        ecdsa_recover(get_crypto_or_die().nist256p1, signature, digest)
    }
}

/// Ed25519 signing and verification.
pub mod ed25519 {
    use super::*;

    /// Verifies an Ed25519 `signature` over `message` against `public_key`.
    ///
    /// Returns `Err` if `message` is empty.
    pub fn sign_open(public_key: &[u8; 32], signature: &[u8; 64], message: &[u8]) -> Result<bool> {
        if message.is_empty() {
            return Err(Error::DataError("Message is empty"));
        }

        let result = ed25519_sign_open(public_key, signature, message);
        Ok(result == 0)
    }

    /// Uses public key to verify the signature of the message. Returns True on success.
    pub fn verify(public_key: &[u8; 32], signature: &[u8; 64], message: &[u8]) -> bool {
        if message.len() == 0 {
            return false; // Empty message is not allowed
        }

        0 == unsafe {
            unwrap!(get_crypto_or_die().ed25519_sign_open)(
                message.as_ptr(),
                message.len(),
                public_key.as_ptr() as *const _,
                signature.as_ptr() as *const _,
            )
        }
    }

    /// Combines a list of public keys used in COSI cosigning scheme.
    pub fn cosi_combine_publickeys(pks: &[[u8; 32]]) -> Result<[u8; 32]> {
        let n = pks.len();

        if n > 15 {
            // Can't combine more than 15 COSI signatures
            return Err(Error::DataError("Too many COSI signatures"));
        }

        let mut res = [0u8; 32];
        let result = ed25519_cosi_combine_publickeys(pks, &mut res);
        if result == 0 {
            Ok(res)
        } else {
            Err(Error::DataError("Failed to combine COSI public keys"))
        }
    }
}

/// SHA-3 family hashers (Keccak-256/512, SHA3-256/512), all implementing [`Hasher`].
pub mod sha3 {
    #[cfg(not(feature = "test"))]
    pub use crate::low_level_api::{Keccak256, Keccak512, Sha3_256 as Sha256, Sha3_512 as Sha512};
    #[cfg(feature = "test")]
    pub use crate::mock::{Keccak256, Keccak512, Sha3_256 as Sha256, Sha3_512 as Sha512};
}

/// SHA-2 family hashers (SHA-256/512), implementing [`Hasher`].
pub mod sha2 {
    #[cfg(not(feature = "test"))]
    pub use crate::low_level_api::{Sha256, Sha512};
    #[cfg(feature = "test")]
    pub use crate::mock::{Sha256, Sha512};
}

/// HMAC over SHA-256/512, implementing [`Hasher`].
pub mod hmac {
    #[cfg(not(feature = "test"))]
    pub use crate::low_level_api::{HmacSha256, HmacSha512};
    #[cfg(feature = "test")]
    pub use crate::mock::{HmacSha256, HmacSha512};
}

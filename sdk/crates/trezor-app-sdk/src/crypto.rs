//! High-level crypto API
//!
//! This module provides user-friendly functions for interacting with the Trezor crypto.
//! ```

// Re-export the archived types for convenience
pub use rkyv::Archived;
use rkyv::api::low::deserialize;
use rkyv::rancor::Failure;
use rkyv::to_bytes;
use trezor_structs::TrezorCryptoEnum;
pub use trezor_structs::{String, TrezorCryptoResult};

use crate::core_services::services_or_die;
use crate::ipc::IpcMessage;
pub use crate::low_level_api::ffi::{HMAC_SHA256_CTX, SHA256_CTX, SHA512_CTX};
use crate::low_level_api::get_crypto_or_die;
pub use crate::low_level_api::{ed25519_cosi_combine_publickeys, ed25519_sign_open};
use crate::service::{CoreIpcService, NoUtilHandler};
use crate::util::Timeout;
use crate::{Error, Result, unwrap};
pub type ArchivedTrezorCryptoEnum<'a> = Archived<TrezorCryptoEnum<'a>>;

#[cfg(not(feature = "test"))]
pub use crate::low_level_api::{Keccak256, Sha3_256, Sha256, Sha512};
#[cfg(feature = "test")]
pub use crate::mock::{Keccak256, Sha3_256, Sha256, Sha512};

// ============================================================================
// Helper Functions
// ============================================================================

type CryptoResult = Result<TrezorCryptoResult>;

fn ipc_crypto_call<'a>(value: &TrezorCryptoEnum<'a>) -> CryptoResult {
    let bytes = unwrap!(to_bytes::<Failure>(value));
    let message = IpcMessage::new(value.id() as _, &bytes);
    let result = services_or_die().call(
        CoreIpcService::Crypto,
        &message,
        Timeout::max(),
        &NoUtilHandler {},
    )?;

    // Safe validation using bytecheck before accessing archived data
    let archived = unwrap!(rkyv::access::<Archived<TrezorCryptoResult>, Failure>(
        result.data()
    ));
    let deserialized = unwrap!(deserialize::<TrezorCryptoResult, Failure>(archived));
    Ok(deserialized)
}

// ============================================================================
// Public crypto Functions
// ============================================================================

/// Show a confirmation dialog with title and content
///
/// Returns `Ok(xpub)` if successful or an error otherwise.
pub fn get_xpub(address_n: &[u32]) -> Result<String<150>> {
    let value = TrezorCryptoEnum::GetXpub {
        address_n: address_n.into(),
    };

    let res = ipc_crypto_call(&value);
    if let Ok(TrezorCryptoResult::Xpub(xpub)) = res {
        Ok(xpub)
    } else {
        // TODO: proper error type
        Err(Error::DataError("Failed to get xpub"))
    }
}

pub fn get_eth_pubkey_hash(
    address_n: &[u32],
    encoded_network: Option<&[u8]>,
    encoded_token: Option<&[u8]>,
    chain_id: Option<u64>,
) -> Result<[u8; 20]> {
    let value = TrezorCryptoEnum::GetEthPubkeyHash {
        address_n: address_n.into(),
        encoded_network: encoded_network.map(|network| network.into()),
        encoded_token: encoded_token.map(|token| token.into()),
        chain_id,
    };

    let res = ipc_crypto_call(&value);

    if let Ok(TrezorCryptoResult::EthPubkeyHash(hash)) = res {
        Ok(hash)
    } else {
        // TODO: proper error type
        Err(Error::DataError("Failed to get ethereum pubkey hash"))
    }
}

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
        Err(Error::DataError("Failed to sign typed hash"))
    }
}

pub fn check_address_mac(
    address_n: &[u32],
    mac: &[u8; 32],
    address: &str,
    encoded_network: Option<&[u8]>,
) -> Result<bool> {
    let value = TrezorCryptoEnum::CheckAddressMac {
        address_n: address_n.into(),
        mac: *mac,
        address: address.into(),
        encoded_network: encoded_network.map(|network| network.into()),
    };

    let res = ipc_crypto_call(&value);

    if let Ok(TrezorCryptoResult::Boolean(valid)) = res {
        Ok(valid)
    } else {
        // TODO: proper error type
        Err(Error::DataError("Failed to check address MAC"))
    }
}

pub fn get_address_mac(
    address_n: &[u32],
    address: &str,
    encoded_network: Option<&[u8]>,
) -> Result<[u8; 32]> {
    let value = TrezorCryptoEnum::GetAddressMac {
        address_n: address_n.into(),
        address: address.into(),
        encoded_network: encoded_network.map(|network| network.into()),
    };

    let res = ipc_crypto_call(&value);

    if let Ok(TrezorCryptoResult::AddressMac(mac)) = res {
        Ok(mac)
    } else {
        // TODO: proper error type
        Err(Error::DataError("Failed to get address MAC"))
    }
}

pub fn verify_nonce_cache(nonce: &[u8]) -> Result<bool> {
    let value = TrezorCryptoEnum::VerifyNonceCache {
        nonce: nonce.into(),
    };

    let res = ipc_crypto_call(&value);

    if let Ok(TrezorCryptoResult::Boolean(valid)) = res {
        Ok(valid)
    } else {
        // TODO: proper error type
        Err(Error::DataError("Failed to verify nonce cache"))
    }
}

pub fn verify_derivation_path(
    address_n: &[u32],
    encoded_network: Option<&[u8]>,
    encoded_token: Option<&[u8]>,
    chain_id: Option<u64>,
) -> Result<()> {
    let value = TrezorCryptoEnum::VerifyDerivationPath {
        address_n: address_n.into(),
        encoded_network: encoded_network.map(|network| network.into()),
        encoded_token: encoded_token.map(|token| token.into()),
        chain_id,
    };

    let res = ipc_crypto_call(&value);

    if matches!(res, Ok(TrezorCryptoResult::Boolean(true))) {
        Ok(())
    } else {
        // TODO: proper error type
        Err(Error::DataError("Forbidden key path"))
    }
}

/// def verify_recover(signature: AnyBytes, digest: AnyBytes) -> bytes:
///     """
///     Uses signature of the digest to verify the digest and recover the public
///     key. Returns public key on success, None if the signature is invalid.
///     """
pub fn secp256k1_verify_recover(
    signature: &[u8; 65],
    digest: &[u8; 32],
) -> Option<([u8; 65], usize)> {
    let mut recid = signature[0] - 27;

    if recid >= 8 {
        return None; // Invalid recovery id
    }

    let compressed = recid >= 4;
    recid &= 3;
    let mut pub_key = [0u8; 65];
    let secp256k1 = unsafe { &*get_crypto_or_die().secp256k1 };

    if unsafe {
        (get_crypto_or_die().ecdsa_recover_pub_from_sig)(
            secp256k1,
            &mut pub_key as *mut u8,
            &signature[1],
            digest.as_ptr(),
            recid.into(),
        )
    } != 0
    {
        return None; // Recovery failed
    }

    if compressed {
        pub_key[0] = 0x02 | (pub_key[64] & 1);
    };

    Some((pub_key, if compressed { 33 } else { 65 }))
}

/// Uses public key to verify the signature of the digest.
/// Returns True on success.
pub fn nist256p1_verify(public_key: &[u8], signature: &[u8], digest: &[u8; 32]) -> bool {
    if public_key.len() != 33 && public_key.len() != 65 {
        return false; // Invalid input lengths
    }
    if signature.len() != 64 && signature.len() != 65 {
        return false; // Invalid signature length
    }

    let offset = if signature.len() == 65 { 1 } else { 0 };
    let nist256p1 = unsafe { &*get_crypto_or_die().nist256p1 };
    unsafe {
        (get_crypto_or_die().ecdsa_verify_digest)(
            nist256p1,
            public_key.as_ptr(),
            signature.as_ptr().byte_offset(offset),
            digest.as_ptr(),
        ) == 0
    }
}

pub trait Hasher {
    // Required methods
    fn update(&mut self, input: &[u8]);
    fn finalize(&mut self, output: &mut [u8]);
}

//! High-level crypto API
//!
//! This module provides user-friendly functions for interacting with the Trezor crypto.
//! ```

pub use rkyv::Archived;
use rkyv::rancor::Failure;
use rkyv::to_bytes;

use crate::app_runtime2::get_crypto_or_die;
use crate::error::{Result, ResultExt as _};
use crate::structs::TrezorCryptoEnum;
pub use crate::structs::{ArchivedTrezorCryptoResult, TrezorCryptoResult};
use crate::traits::service::{CoreIpcService, IpcError, MessageDyn as _};
use crate::util::Timeout;
use crate::{Error, core_services, unwrap};
pub type ArchivedTrezorCryptoEnum<'a> = Archived<TrezorCryptoEnum<'a>>;
type ArchivedTrezorCryptoResult_<'a> = Archived<TrezorCryptoResult_<'a>>;

#[cfg(not(feature = "test"))]
pub use crate::low_level_api::{Keccak256, Sha3_256, Sha256, Sha512};
#[cfg(feature = "test")]
pub use crate::mock::{Keccak256, Sha3_256, Sha256, Sha512};

// ============================================================================
// Helper Functions
// ============================================================================

pub enum CryptoError {
    IpcCallFailed,
}

impl<'a> From<IpcError<'a>> for CryptoError {
    fn from(_error: IpcError<'a>) -> Self {
        CryptoError::IpcCallFailed
    }
}

type CryptoResult = Result<TrezorCryptoResult, CryptoError>;

fn ipc_crypto_call<'a>(value: &TrezorCryptoEnum<'a>) -> CryptoResult {
    let bytes = unwrap!(to_bytes::<Failure>(value));

    let result = core_services::call(
        CoreIpcService::Crypto,
        value.id() as _,
        bytes.as_ref(),
        Timeout::max(),
    )?;

    // Safe validation using bytecheck before accessing archived data
    let archived = unwrap!(rkyv::access::<Archived<TrezorCryptoResult>, Failure>(
        result.data().into()
    ));

    let result =
        match unsafe { rkyv::access_unchecked::<Archived<TrezorCryptoResult_>>(result.data()) } {
            ArchivedTrezorCryptoResult_::AddressMac(mac) => TrezorCryptoResult::AddressMac(*mac),
            ArchivedTrezorCryptoResult_::Boolean(valid) => TrezorCryptoResult::Boolean(*valid),
            ArchivedTrezorCryptoResult_::Xpub(xpub) => TrezorCryptoResult::Xpub(*xpub),
            ArchivedTrezorCryptoResult_::PublicKey(xpub) => {
                TrezorCryptoResult::PublicKey(Vec::from(xpub.as_slice()))
            }
            ArchivedTrezorCryptoResult_::Signature(signature) => {
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

pub trait Hasher {
    // Required methods
    fn update(&mut self, input: &[u8]);
    fn finalize(&mut self, output: &mut [u8]);
}

/// Show a confirmation dialog with title and content
///
/// Returns `Ok(xpub)` if successful or an error otherwise.
pub fn get_xpub(address_n: &[u32]) -> Result<String, CryptoError> {
    let value = TrezorCryptoEnum::GetXpub {
        address_n: address_n.into(),
        xpub_magic,
    };

    let res = ipc_crypto_call(&value);
    if let Ok(TrezorCryptoResult::XpubBytes(xpub)) = res {
        let xpub_str = get_crypto_or_die().base58check_encode((&xpub[..]).into());
        Ok(xpub_str.as_str().into())
        // TODO: do we need to copy the string? or is it enough to propagate stabby's type
    } else {
        // TODO: proper error type
        Err(CryptoError::IpcCallFailed.into())
    }
}

pub fn get_xpub_bytes(address_n: &[u32]) -> Result<[u8; 33], CryptoError> {
    let value = TrezorCryptoEnum::GetXpubBytes {
        address_n: address_n.into(),
        compressed,
    };

    let res = ipc_crypto_call(&value);
    if let Ok(TrezorCryptoResult::PublicKey(xpub)) = res {
        Ok(xpub)
    } else {
        // TODO: proper error type
        Err(CryptoError::IpcCallFailed.into())
    }
}

pub fn sign_typed_hash(
    address_n: &[u32],
    hash: &[u8; 32],
    encoded_network: Option<&[u8]>,
    encoded_token: Option<&[u8]>,
    chain_id: Option<u64>,
    show_progress: bool,
) -> Result<[u8; 65], CryptoError> {
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
        Err(CryptoError::IpcCallFailed.into())
    }
}

pub fn check_address_mac(
    address_n: &[u32],
    mac: &[u8; 32],
    address: &str,
    encoded_network: Option<&[u8]>,
) -> Result<bool, CryptoError> {
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
        Err(CryptoError::IpcCallFailed.into())
    }
}

pub fn get_address_mac(
    address_n: &[u32],
    address: &str,
    encoded_network: Option<&[u8]>,
) -> Result<[u8; 32], CryptoError> {
    let value = TrezorCryptoEnum::GetAddressMac {
        address_n: address_n.into(),
        address: address.into(),
    };

    let res = ipc_crypto_call(&value);

    if let Ok(TrezorCryptoResult::AddressMac(mac)) = res {
        Ok(mac)
    } else {
        // TODO: proper error type
        Err(CryptoError::IpcCallFailed.into())
    }
}

pub fn verify_nonce_cache(nonce: &[u8]) -> Result<bool, CryptoError> {
    let value = TrezorCryptoEnum::VerifyNonceCache {
        nonce: nonce.into(),
    };

    let res = ipc_crypto_call(&value);

    if let Ok(TrezorCryptoResult::Boolean(valid)) = res {
        Ok(valid)
    } else {
        // TODO: proper error type
        Err(CryptoError::IpcCallFailed.into())
    }
}

pub fn verify_derivation_path(
    address_n: &[u32],
    encoded_network: Option<&[u8]>,
    encoded_token: Option<&[u8]>,
    chain_id: Option<u64>,
) -> Result<(), CryptoError> {
    let value = TrezorCryptoEnum::VerifyDerivationPath {
        address_n: address_n.into(),
        encoded_network: encoded_network.map(|network| network.into()),
        encoded_token: encoded_token.map(|token| token.into()),
        chain_id,
    };

    pub fn verify(public_key: &[u8], signature: &[u8], digest: &[u8; 32]) -> bool {
        ecdsa_verify_digest(get_crypto_or_die().secp256k1, public_key, signature, digest)
    }

    if matches!(res, Ok(TrezorCryptoResult::Boolean(true))) {
        Ok(())
    } else {
        // TODO: proper error type
        Err(CryptoError::IpcCallFailed.into())
    }
}

/// def verify_recover(signature: AnyBytes, digest: AnyBytes) -> bytes:
///     """
///     Uses signature of the digest to verify the digest and recover the public
///     key. Returns public key on success, None if the signature is invalid.
///     """
pub fn secp256k1_verify_recover(signature: &[u8; 65], digest: &[u8; 32]) -> Option<Vec<u8>> {
    let mut recid = signature[0] - 27;

    pub fn verify(public_key: &[u8], signature: &[u8], digest: &[u8; 32]) -> bool {
        ecdsa_verify_digest(get_crypto_or_die().nist256p1, public_key, signature, digest)
    }

    let compressed = recid >= 4;
    recid &= 3;
    let mut pub_key = [0u8; 65];
    let secp256k1 = unsafe { &*get_crypto_or_die().secp256k1 };

    if unsafe {
        unwrap!(get_crypto_or_die().ecdsa_recover_pub_from_sig)(
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

    let len = if compressed { 33 } else { 65 };
    let mut result = Vec::with_capacity(65);
    result.extend_from_slice(&pub_key[..len]);
    Some(result)
}

pub fn ecdsa_get_public_key65(address_n: &[u32]) -> Result<[u8; 65]> {
    let value = TrezorCryptoEnum::EcdsaPublicKey65 {
        address_n: address_n.into(),
    };

    let res = ipc_crypto_call(&value);
    if let Ok(TrezorCryptoResult::EcdsaPublicKey65(pubkey)) = res {
        Ok(pubkey)
    } else {
        Err(Error::ApiError(crate::low_level_api::ApiError::Failed))?
    }
}

pub mod ed25519 {
    use super::*;

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

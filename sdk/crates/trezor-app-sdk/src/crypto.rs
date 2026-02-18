//! High-level crypto API
//!
//! This module provides user-friendly functions for interacting with the Trezor crypto.
//! ```

// Re-export the archived types for convenience
pub use rkyv::Archived;
use rkyv::api::low::deserialize;
use rkyv::rancor::Failure;
use rkyv::to_bytes;
pub use trezor_structs::TrezorCryptoResult;
use trezor_structs::{DerivationPath, LongString, TrezorCryptoEnum, TypedHash};

use crate::core_services::services_or_die;
use crate::ipc::IpcMessage;
pub use crate::low_level_api::ffi::SHA256_CTX;
use crate::low_level_api::get_crypto_or_die;
pub use crate::low_level_api::{
    ed25519_cosi_combine_publickeys, ed25519_sign_open, keccak_256, sha3_256,
};
use crate::service::{CoreIpcService, Error, NoUtilHandler};
use crate::util::Timeout;
pub type ArchivedTrezorCryptoResult = Archived<TrezorCryptoResult>;
pub type ArchivedTrezorCryptoEnum = Archived<TrezorCryptoEnum>;

// ============================================================================
// Helper Functions
// ============================================================================

type Result<T> = core::result::Result<T, Error<'static>>;
type CryptoResult = Result<TrezorCryptoResult>;

fn ipc_crypto_call(value: &TrezorCryptoEnum) -> CryptoResult {
    let bytes = to_bytes::<Failure>(value).unwrap();
    let message = IpcMessage::new(0, &bytes);
    let result = services_or_die().call(
        CoreIpcService::Crypto,
        &message,
        Timeout::max(),
        &NoUtilHandler {},
    )?;

    // Safe validation using bytecheck before accessing archived data
    let archived = rkyv::access::<ArchivedTrezorCryptoResult, Failure>(result.data()).unwrap();
    let deserialized = deserialize::<TrezorCryptoResult, Failure>(archived).unwrap();
    Ok(deserialized)
}

// ============================================================================
// Public crypto Functions
// ============================================================================

/// Show a confirmation dialog with title and content
///
/// Returns `Ok(xpub)` if successful or an error otherwise.
pub fn get_xpub(address_n: &[u32]) -> Result<LongString> {
    let value = TrezorCryptoEnum::GetXpub {
        address_n: DerivationPath::from_slice(address_n).unwrap(),
    };

    let res = ipc_crypto_call(&value);

    if let Ok(TrezorCryptoResult::Xpub(xpub)) = res {
        Ok(xpub)
    } else {
        // TODO: use proper error type
        Err(Error::Timeout)
    }
}

pub fn get_eth_pubkey_hash(address_n: &[u32]) -> Result<[u8; 20]> {
    let value = TrezorCryptoEnum::GetEthPubkeyHash {
        address_n: DerivationPath::from_slice(address_n).unwrap(),
    };

    let res = ipc_crypto_call(&value);

    if let Ok(TrezorCryptoResult::EthPubkeyHash(hash)) = res {
        Ok(hash)
    } else {
        // TODO: use proper error type
        Err(Error::Timeout)
    }
}

pub fn sign_typed_hash(address_n: &[u32], hash: &[u8]) -> Result<[u8; 64]> {
    let value = TrezorCryptoEnum::SignTypedHash {
        address_n: DerivationPath::from_slice(address_n).unwrap(),
        hash: TypedHash::from_slice(hash).unwrap(),
    };

    let res = ipc_crypto_call(&value);

    if let Ok(TrezorCryptoResult::Signature(signature)) = res {
        Ok(signature)
    } else {
        // TODO: use proper error type
        Err(Error::Timeout)
    }
}

pub struct Sha256 {
    ctx: SHA256_CTX,
}

impl Sha256 {
    pub fn new(data: Option<&[u8]>) -> Self {
        let mut ctx = SHA256_CTX {
            state: [0u32; 8],
            bitcount: 0,
            buffer: [0u32; 16],
        };
        unsafe { (get_crypto_or_die().sha256_Init)(&mut ctx) };
        if let Some(data) = data {
            unsafe { (get_crypto_or_die().sha256_Update)(&mut ctx, data.as_ptr(), data.len()) };
        }
        Self { ctx }
    }

    pub fn update(&mut self, data: &[u8]) {
        unsafe { (get_crypto_or_die().sha256_Update)(&mut self.ctx, data.as_ptr(), data.len()) };
    }

    pub fn digest(mut self) -> [u8; 32] {
        let mut digest = [0u8; 32];
        unsafe { (get_crypto_or_die().sha256_Final)(&mut self.ctx, digest.as_mut_ptr()) };
        digest
    }
}

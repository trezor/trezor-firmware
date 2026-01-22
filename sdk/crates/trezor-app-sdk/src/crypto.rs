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
use trezor_structs::{DerivationPath, LongString, TrezorCryptoEnum};

use crate::core_services::services_or_die;
use crate::ipc::IpcMessage;
use crate::low_level_api::ffi::HDNode;
use crate::service::{CoreIpcService, Error};
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
    let result = services_or_die().call(CoreIpcService::Crypto, &message, Timeout::max())?;

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

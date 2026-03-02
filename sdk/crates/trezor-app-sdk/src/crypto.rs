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
use trezor_structs::{
    DerivationPath, LongString, ShortBuffer, ShortString, TrezorCryptoEnum, TypedHash,
};

use crate::core_services::services_or_die;
use crate::ipc::IpcMessage;
pub use crate::low_level_api::ffi::{HMAC_SHA256_CTX, SHA256_CTX, SHA512_CTX};
use crate::low_level_api::get_crypto_or_die;
pub use crate::low_level_api::{
    ed25519_cosi_combine_publickeys, ed25519_sign_open, keccak_256, sha3_256,
};
use crate::service::{CoreIpcService, Error, NoUtilHandler};
use crate::util::Timeout;
use crate::{info, unwrap};
pub type ArchivedTrezorCryptoResult = Archived<TrezorCryptoResult>;
pub type ArchivedTrezorCryptoEnum = Archived<TrezorCryptoEnum>;

// ============================================================================
// Helper Functions
// ============================================================================

type Result<T> = core::result::Result<T, Error<'static>>;
type CryptoResult = Result<TrezorCryptoResult>;

fn ipc_crypto_call(value: &TrezorCryptoEnum) -> CryptoResult {
    let bytes = unwrap!(to_bytes::<Failure>(value));
    let message = IpcMessage::new(value.id() as _, &bytes);
    let result = services_or_die().call(
        CoreIpcService::Crypto,
        &message,
        Timeout::max(),
        &NoUtilHandler {},
    )?;

    // Safe validation using bytecheck before accessing archived data
    let archived = unwrap!(rkyv::access::<ArchivedTrezorCryptoResult, Failure>(
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
pub fn get_xpub(address_n: &[u32]) -> Result<LongString> {
    let value = TrezorCryptoEnum::GetXpub {
        address_n: unwrap!(DerivationPath::from_slice(address_n)),
    };

    let res = ipc_crypto_call(&value);

    if let Ok(TrezorCryptoResult::Xpub(xpub)) = res {
        Ok(xpub)
    } else {
        // TODO: use proper error type
        Err(Error::Timeout)
    }
}

pub fn get_eth_pubkey_hash(
    address_n: &[u32],
    encoded_network: Option<&[u8]>,
    encoded_token: Option<&[u8]>,
) -> Result<[u8; 20]> {
    let value = TrezorCryptoEnum::GetEthPubkeyHash {
        address_n: unwrap!(DerivationPath::from_slice(address_n)),
        encoded_network: encoded_network.map(|network| unwrap!(ShortBuffer::from_slice(network))),
        encoded_token: encoded_token.map(|token| unwrap!(ShortBuffer::from_slice(token))),
    };

    let res = ipc_crypto_call(&value);

    if let Ok(TrezorCryptoResult::EthPubkeyHash(hash)) = res {
        Ok(hash)
    } else {
        // TODO: use proper error type
        Err(Error::Timeout)
    }
}

pub fn sign_typed_hash(
    address_n: &[u32],
    hash: &[u8],
    encoded_network: Option<&[u8]>,
    encoded_token: Option<&[u8]>,
) -> Result<[u8; 64]> {
    let value = TrezorCryptoEnum::SignTypedHash {
        address_n: unwrap!(DerivationPath::from_slice(address_n)),
        hash: unwrap!(TypedHash::from_slice(hash)),
        encoded_network: encoded_network.map(|network| unwrap!(ShortBuffer::from_slice(network))),
        encoded_token: encoded_token.map(|token| unwrap!(ShortBuffer::from_slice(token))),
    };

    let res = ipc_crypto_call(&value);

    if let Ok(TrezorCryptoResult::Signature(signature)) = res {
        Ok(signature)
    } else {
        // TODO: use proper error type
        Err(Error::Timeout)
    }
}

pub fn get_address_mac(
    address_n: &[u32],
    key: &str,
    encoded_network: Option<&[u8]>,
) -> Result<[u8; 32]> {
    let value = TrezorCryptoEnum::GetAddressMac {
        address_n: unwrap!(DerivationPath::from_slice(address_n)),
        address: unwrap!(ShortString::from_str(key)),
        encoded_network: encoded_network.map(|network| unwrap!(ShortBuffer::from_slice(network))),
    };

    let res = ipc_crypto_call(&value);

    if let Ok(TrezorCryptoResult::AddressMac(mac)) = res {
        Ok(mac)
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

    pub fn digest_size() -> usize {
        32
    }
}

impl Drop for Sha256 {
    fn drop(&mut self) {
        unsafe {
            core::ptr::write_volatile(&mut self.ctx, core::mem::zeroed());
        }
    }
}

pub struct Sha512 {
    ctx: SHA512_CTX,
}

impl Sha512 {
    pub fn new(data: Option<&[u8]>) -> Self {
        let mut ctx = SHA512_CTX {
            state: [0u64; 8],
            bitcount: [0u64; 2],
            buffer: [0u64; 16],
        };
        unsafe { (get_crypto_or_die().sha512_Init)(&mut ctx) };
        if let Some(data) = data {
            unsafe { (get_crypto_or_die().sha512_Update)(&mut ctx, data.as_ptr(), data.len()) };
        }
        Self { ctx }
    }

    pub fn update(&mut self, data: &[u8]) {
        unsafe { (get_crypto_or_die().sha512_Update)(&mut self.ctx, data.as_ptr(), data.len()) };
    }

    pub fn digest(mut self) -> [u8; 64] {
        let mut digest = [0u8; 64];
        unsafe { (get_crypto_or_die().sha512_Final)(&mut self.ctx, digest.as_mut_ptr()) };
        digest
    }

    pub fn digest_size() -> usize {
        64
    }
}

impl Drop for Sha512 {
    fn drop(&mut self) {
        unsafe {
            core::ptr::write_volatile(&mut self.ctx, core::mem::zeroed());
        }
    }
}

pub struct HmacSha256 {
    ctx: HMAC_SHA256_CTX,
}

impl HmacSha256 {
    pub fn new(key: &[u8], data: Option<&[u8]>) -> Self {
        let mut ctx = HMAC_SHA256_CTX {
            o_key_pad: [0u8; 64],
            ctx: SHA256_CTX {
                state: [0u32; 8],
                bitcount: 0,
                buffer: [0u32; 16],
            },
        };
        unsafe { (get_crypto_or_die().hmac_sha256_Init)(&mut ctx, key.as_ptr(), key.len() as u32) };
        if let Some(data) = data {
            unsafe {
                (get_crypto_or_die().hmac_sha256_Update)(&mut ctx, data.as_ptr(), data.len() as u32)
            };
        }
        Self { ctx }
    }

    pub fn update(&mut self, data: &[u8]) {
        unsafe {
            (get_crypto_or_die().hmac_sha256_Update)(
                &mut self.ctx,
                data.as_ptr(),
                data.len() as u32,
            )
        };
    }

    pub fn digest(mut self) -> [u8; 32] {
        let mut digest = [0u8; 32];
        unsafe { (get_crypto_or_die().hmac_sha256_Final)(&mut self.ctx, digest.as_mut_ptr()) };
        digest
    }

    pub fn digest_size() -> usize {
        32
    }
}

impl Drop for HmacSha256 {
    fn drop(&mut self) {
        unsafe {
            core::ptr::write_volatile(&mut self.ctx, core::mem::zeroed());
        }
    }
}

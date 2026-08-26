//! High-level crypto API
//!
//! This module provides user-friendly functions for interacting with the Trezor crypto.
//!
//! [`get_address_mac`] and friends round-trip through Core over IPC (via the
//! stable-ABI [`IpcRemote`](crate::traits::service::IpcRemote) handed to this
//! app), since they touch key material Core alone holds.
//!
//! [`sha2`] and [`sha3`] are local (non-IPC) hashers — hashing needs no secret
//! material, so instead of Core they call straight through the local
//! `CryptoV1::get_hasher` vtable (see the module docs).

use rkyv::rancor::Failure;
use rkyv::{Archived, to_bytes};

use crate::alloc_types::Vec;
use crate::app_runtime2::get_ipc_or_die;
use crate::structs::{TrezorCryptoEnum, TrezorCryptoResultRef};
use crate::traits::service::{CoreIpcService, IpcRemoteDyn as _, MessageDyn as _, MessageRef};
use crate::util::Timeout;
use crate::{Error, IntoAppResult, Result, ResultExt};

pub type ArchivedTrezorCryptoEnum<'a> = Archived<TrezorCryptoEnum<'a>>;
pub type ArchivedTrezorCryptoResultRef<'a> = Archived<TrezorCryptoResultRef<'a>>;

// ============================================================================
// Helper Functions
// ============================================================================

/// Serializes `value` and sends it to Core's crypto service, returning the
/// raw response message. Callers deserialize it themselves (via
/// [`ArchivedTrezorCryptoResultRef`]) so the response stays borrowed from
/// this message rather than being copied out through a shared helper.
fn ipc_crypto_call(value: &TrezorCryptoEnum<'_>) -> Result<MessageRef<'static>> {
    let bytes = to_bytes::<Failure>(value)
        .map_err(|_| Error::ServiceError)
        .c()?;
    get_ipc_or_die()
        .call(
            CoreIpcService::Crypto.into(),
            value.id() as u16,
            bytes.as_ref().into(),
            Timeout::max().as_ms(),
        )
        .into_app_result()
        .c()
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

/// Derives the extended public key (xpub) for `address_n`, base58check-encoded
/// with `xpub_magic` as its version bytes (e.g. the "xpub"/"ypub"/"zpub"
/// prefix bytes for the coin/script type in use).
pub fn get_xpub(address_n: &[u32], xpub_magic: u32) -> Result<[u8; 111]> {
    let value = TrezorCryptoEnum::GetXpub {
        address_n: address_n.into(),
        xpub_magic,
    };
    let message = ipc_crypto_call(&value)?;
    let archived =
        rkyv::access::<ArchivedTrezorCryptoResultRef<'_>, Failure>(message.data().into())
            .map_err(|_| Error::ServiceError)?;

    match archived {
        ArchivedTrezorCryptoResultRef::Xpub(xpub) => Ok(*xpub),
        _ => Err(Error::ServiceError),
    }
}

/// Derives the public key for `address_n`.
pub fn get_public_key(address_n: &[u32], compressed: bool) -> Result<Vec<u8>> {
    let value = TrezorCryptoEnum::GetPublicKey {
        address_n: address_n.into(),
        compressed,
    };
    let message = ipc_crypto_call(&value)?;
    let archived =
        rkyv::access::<ArchivedTrezorCryptoResultRef<'_>, Failure>(message.data().into())
            .map_err(|_| Error::ServiceError)?;

    match archived {
        ArchivedTrezorCryptoResultRef::PublicKey(key) => {
            let mut owned = Vec::new();
            owned.extend_from_slice(key.as_ref());
            Ok(owned)
        }
        _ => Err(Error::ServiceError),
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
    let message = ipc_crypto_call(&value)?;
    let archived =
        rkyv::access::<ArchivedTrezorCryptoResultRef<'_>, Failure>(message.data().into())
            .map_err(|_| Error::ServiceError)?;

    match archived {
        ArchivedTrezorCryptoResultRef::Signature(signature) => Ok(*signature),
        _ => Err(Error::ServiceError),
    }
}

/// Signs a raw 32-byte digest with the key at `address_n`.
pub fn sign_digest(address_n: &[u32], digest: &[u8; 32], compressed: bool) -> Result<[u8; 65]> {
    let value = TrezorCryptoEnum::SignDigest {
        address_n: address_n.into(),
        digest: *digest,
        compressed,
    };
    let message = ipc_crypto_call(&value)?;
    let archived =
        rkyv::access::<ArchivedTrezorCryptoResultRef<'_>, Failure>(message.data().into())
            .map_err(|_| Error::ServiceError)?;

    match archived {
        ArchivedTrezorCryptoResultRef::Signature(signature) => Ok(*signature),
        _ => Err(Error::ServiceError),
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
    let message = ipc_crypto_call(&value)?;
    let archived =
        rkyv::access::<ArchivedTrezorCryptoResultRef<'_>, Failure>(message.data().into())
            .map_err(|_| Error::ServiceError)?;

    match archived {
        ArchivedTrezorCryptoResultRef::Boolean(valid) => Ok(*valid),
        _ => Err(Error::ServiceError),
    }
}

/// Computes a MAC binding `address_n` to `address`, so a cached `address` can
/// later be re-authenticated via [`check_address_mac`] without a full re-derivation.
pub fn get_address_mac(address_n: &[u32], address: &str) -> Result<[u8; 32]> {
    let value = TrezorCryptoEnum::GetAddressMac {
        address_n: address_n.into(),
        address: address.into(),
    };
    let message = ipc_crypto_call(&value)?;
    let archived =
        rkyv::access::<ArchivedTrezorCryptoResultRef<'_>, Failure>(message.data().into())
            .map_err(|_| Error::ServiceError)?;

    match archived {
        ArchivedTrezorCryptoResultRef::AddressMac(mac) => Ok(*mac),
        _ => Err(Error::ServiceError),
    }
}

/// Checks `nonce` against Core's cached-nonce store, returning whether it's still valid.
pub fn verify_nonce_cache(nonce: &[u8]) -> Result<bool> {
    let value = TrezorCryptoEnum::VerifyNonceCache {
        nonce: nonce.into(),
    };
    let message = ipc_crypto_call(&value)?;
    let archived =
        rkyv::access::<ArchivedTrezorCryptoResultRef<'_>, Failure>(message.data().into())
            .map_err(|_| Error::ServiceError)?;

    match archived {
        ArchivedTrezorCryptoResultRef::Boolean(valid) => Ok(*valid),
        _ => Err(Error::ServiceError),
    }
}

/// SHA-3 family hashers (Keccak-256), implementing [`Hasher`].
///
/// Hashing is a local, non-secret operation, so unlike the functions above it
/// doesn't go through Core's IPC — it calls straight through the local
/// `CryptoV1::get_hasher` vtable instead (except under `test`, where it
/// delegates to a real software implementation via [`crate::mock`] instead of
/// requiring [`crate::mock::sdk_init`] to have populated that vtable).
pub mod sha3 {
    #[cfg(not(feature = "test"))]
    pub use real::Keccak256;

    #[cfg(feature = "test")]
    pub use crate::mock::Keccak256;

    #[cfg(not(feature = "test"))]
    mod real {
        use stabby::slice::Slice;

        use crate::app_runtime2::get_crypto_or_die;
        use crate::crypto::Hasher;
        use crate::traits::crypto::{BoxedHasher, CryptoV1Dyn as _, HashingAlgorithm};

        pub struct Keccak256(BoxedHasher);

        impl Keccak256 {
            /// Creates a new hasher, optionally pre-seeded with `data`.
            pub fn new(data: Option<&[u8]>) -> Self {
                let mut hasher = Self(get_crypto_or_die().get_hasher(HashingAlgorithm::Keccak256));
                if let Some(data) = data {
                    hasher.update(data);
                }
                hasher
            }
        }

        impl Hasher for Keccak256 {
            fn update(&mut self, input: &[u8]) {
                get_crypto_or_die().hasher_update(self.0, Slice::from(input));
            }

            fn finalize(&mut self, output: &mut [u8]) {
                output.copy_from_slice(&get_crypto_or_die().hasher_finalize(self.0));
            }
        }
    }
}

/// SHA-2 family hashers (SHA-256), implementing [`Hasher`].
///
/// See [`sha3`] — calls straight through the local `CryptoV1::get_hasher`
/// vtable, no IPC round trip (except under `test`, see [`sha3`]).
pub mod sha2 {
    #[cfg(not(feature = "test"))]
    pub use real::Sha256;

    #[cfg(feature = "test")]
    pub use crate::mock::Sha256;

    #[cfg(not(feature = "test"))]
    mod real {
        use stabby::slice::Slice;

        use crate::app_runtime2::get_crypto_or_die;
        use crate::crypto::Hasher;
        use crate::traits::crypto::{BoxedHasher, CryptoV1Dyn as _, HashingAlgorithm};

        pub struct Sha256(BoxedHasher);

        impl Sha256 {
            /// Creates a new hasher, optionally pre-seeded with `data`.
            pub fn new(data: Option<&[u8]>) -> Self {
                let mut hasher = Self(get_crypto_or_die().get_hasher(HashingAlgorithm::Sha256));
                if let Some(data) = data {
                    hasher.update(data);
                }
                hasher
            }

            /// Finalizes and returns the digest.
            pub fn digest(&mut self) -> [u8; 32] {
                let mut out = [0u8; 32];
                self.finalize(&mut out);
                out
            }
        }

        impl Hasher for Sha256 {
            fn update(&mut self, input: &[u8]) {
                get_crypto_or_die().hasher_update(self.0, Slice::from(input));
            }

            fn finalize(&mut self, output: &mut [u8]) {
                output.copy_from_slice(&get_crypto_or_die().hasher_finalize(self.0));
            }
        }
    }
}

/// HMAC-SHA256, implementing [`Hasher`].
///
/// See [`sha3`] — calls straight through the local `CryptoV1::get_hmac_hasher`
/// vtable, no IPC round trip (except under `test`, see [`sha3`]).
pub mod hmac {
    #[cfg(not(feature = "test"))]
    pub use real::HmacSha256;

    #[cfg(feature = "test")]
    pub use crate::mock::HmacSha256;

    #[cfg(not(feature = "test"))]
    mod real {
        use stabby::slice::Slice;

        use crate::app_runtime2::get_crypto_or_die;
        use crate::crypto::Hasher;
        use crate::traits::crypto::{BoxedHasher, CryptoV1Dyn as _};

        pub struct HmacSha256(BoxedHasher);

        impl HmacSha256 {
            /// Creates a new hasher keyed with `key`, optionally pre-seeded
            /// with `data`.
            pub fn new(key: &[u8], data: Option<&[u8]>) -> Self {
                let mut hasher = Self(get_crypto_or_die().get_hmac_hasher(Slice::from(key)));
                if let Some(data) = data {
                    hasher.update(data);
                }
                hasher
            }

            /// Finalizes and returns the digest.
            pub fn digest(&mut self) -> [u8; 32] {
                let mut out = [0u8; 32];
                self.finalize(&mut out);
                out
            }
        }

        impl Hasher for HmacSha256 {
            fn update(&mut self, input: &[u8]) {
                get_crypto_or_die().hasher_update(self.0, Slice::from(input));
            }

            fn finalize(&mut self, output: &mut [u8]) {
                output.copy_from_slice(&get_crypto_or_die().hasher_finalize(self.0));
            }
        }
    }
}

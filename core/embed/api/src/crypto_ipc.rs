//! The crypto service's IPC messages between the app task and Core.

use rkyv::{Archive, Deserialize, Serialize};
use trezor_app_sdk::structs::{Slice, StrSlice};
use ufmt::derive::uDebug;

/// All crypto operations that can be requested from the app via IPC.
///
/// Built by the app-side `crate::crypto` module, handled by Core in
/// `trezor_lib::crypto_api`.
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize)]
pub enum TrezorCryptoEnum<'a> {
    /// Derive the raw xpub, see `CryptoV1::get_xpub`.
    GetXpub {
        /// A [`Curve`](trezor_app_sdk::traits::crypto::Curve), as its `u8`
        /// value.
        curve: u8,
        /// Derivation path.
        address_n: Slice<'a, u32>,
    },
    /// Derive a public key.
    GetPublicKey {
        /// A [`Curve`](trezor_app_sdk::traits::crypto::Curve), as its `u8`
        /// value.
        curve: u8,
        /// Derivation path.
        address_n: Slice<'a, u32>,
        /// Return the compressed form.
        compressed: bool,
    },
    /// Sign a digest with ECDSA.
    EcdsaSignDigest {
        /// An [`EcdsaCurve`](trezor_app_sdk::traits::crypto::EcdsaCurve), as
        /// its `u8` value.
        curve: u8,
        /// Derivation path.
        address_n: Slice<'a, u32>,
        /// The digest to sign.
        digest: [u8; 32],
        /// Set the recovery header byte for a compressed public key.
        compressed: bool,
        /// A [`CanonicalSig`](trezor_app_sdk::traits::crypto::CanonicalSig), as
        /// its `u8` value.
        canonical: u8,
    },
    /// Sign a message with Ed25519.
    Ed25519Sign {
        /// Derivation path.
        address_n: Slice<'a, u32>,
        /// The message to sign.
        message: Slice<'a, u8>,
    },
    /// Compute the MAC of an address.
    GetAddressMac {
        /// Derivation path of the address.
        address_n: Slice<'a, u32>,
        /// The address.
        address: StrSlice<'a>,
        /// SLIP-44 coin type.
        slip44: u32,
    },
    /// Check the MAC of an address.
    CheckAddressMac {
        /// Derivation path of the address.
        address_n: Slice<'a, u32>,
        /// The MAC to check.
        mac: [u8; 32],
        /// The address.
        address: StrSlice<'a>,
        /// SLIP-44 coin type.
        slip44: u32,
    },
}

impl<'a> TrezorCryptoEnum<'a> {
    /// The IPC message id of the request.
    pub fn id(&self) -> u8 {
        match self {
            Self::GetXpub { .. } => 0,
            Self::GetPublicKey { .. } => 1,
            Self::EcdsaSignDigest { .. } => 2,
            Self::Ed25519Sign { .. } => 3,
            Self::GetAddressMac { .. } => 4,
            Self::CheckAddressMac { .. } => 5,
        }
    }
}

/// Result of a crypto operation, sent by the Core task and borrowed directly
/// from the archived IPC buffer.
///
/// Deliberately generic: each caller knows which shape its operation returns,
/// and checks for it (including any fixed length) itself. Core reports a
/// failed operation as `Boolean(false)`, which no caller expecting data
/// accepts.
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize, Deserialize)]
pub enum TrezorCryptoResult<'a> {
    /// A string.
    String(StrSlice<'a>),
    /// Bytes.
    Bytes(Slice<'a, u8>),
    /// A boolean.
    Boolean(bool),
}

#[cfg(test)]
mod tests {
    extern crate std;

    use super::*;

    /// Ensures every variant of TrezorCryptoEnum has a unique id()
    /// and that no variant is accidentally forgotten.
    #[test]
    fn crypto_ids_are_unique_and_exhaustive() {
        use TrezorCryptoEnum::*;
        let empty_u32: &[u32] = &[];
        let empty_u8: &[u8] = &[];
        let variants: &[(u8, &str)] = &[
            (
                GetXpub {
                    curve: 0,
                    address_n: empty_u32.into(),
                }
                .id(),
                "GetXpub",
            ),
            (
                GetPublicKey {
                    curve: 0,
                    address_n: empty_u32.into(),
                    compressed: false,
                }
                .id(),
                "GetPublicKey",
            ),
            (
                EcdsaSignDigest {
                    curve: 0,
                    address_n: empty_u32.into(),
                    digest: [0u8; 32],
                    compressed: false,
                    canonical: 0,
                }
                .id(),
                "EcdsaSignDigest",
            ),
            (
                Ed25519Sign {
                    address_n: empty_u32.into(),
                    message: empty_u8.into(),
                }
                .id(),
                "Ed25519Sign",
            ),
            (
                GetAddressMac {
                    address_n: empty_u32.into(),
                    address: "".into(),
                    slip44: 0,
                }
                .id(),
                "GetAddressMac",
            ),
            (
                CheckAddressMac {
                    address_n: empty_u32.into(),
                    mac: [0u8; 32],
                    address: "".into(),
                    slip44: 0,
                }
                .id(),
                "CheckAddressMac",
            ),
        ];
        let mut seen = std::collections::HashSet::new();
        for (id, name) in variants {
            assert!(seen.insert(id), "duplicate id {} for variant {}", id, name);
        }
        assert_eq!(variants.len(), 6, "new variant added but test not updated");
    }
}

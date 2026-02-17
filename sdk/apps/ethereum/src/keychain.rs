extern crate alloc;

use crate::paths::KeychainValidator;
use crate::paths::{Bip32Path, PathSchemaTrait};
use alloc::vec::Vec;
use trezor_app_sdk::{Error, Result};

// https://github.com/bitcoin/bips/blob/master/bip-0044.mediawiki
// The BIP44 pattern, overloaded to be used for ETH accounts, as described above
const PATTERN_BIP44_ETH: &str = "m/44'/coin_type'/0'/0/account";

// BIP-44 for basic (legacy) Bitcoin accounts, and widely used for other currencies:
// https://github.com/bitcoin/bips/blob/master/bip-0044.mediawiki
const PATTERN_BIP44: &str = "m/44'/coin_type'/account'/change/address_index";
// BIP-44 public key export, starting at end of the hardened part
const PATTERN_BIP44_PUBKEY: &str = "m/44'/coin_type'/account'/*";
// SEP-0005 for non-UTXO-based currencies, defined by Stellar:
// https://github.com/stellar/stellar-protocol/blob/master/ecosystem/sep-0005.md
const PATTERN_SEP5: &str = "m/44'/coin_type'/account'";
// SEP-0005 Ledger Live legacy path
// https://github.com/trezor/trezor-firmware/issues/1749
const PATTERN_SEP5_LEDGER_LIVE_LEGACY: &str = "m/44'/coin_type'/0'/account";

const PATTERN_CASA: &str = "m/45'/coin_type/account/change/address_index";

pub const PATTERNS_ADDRESS: [&str; 5] = [
    PATTERN_BIP44_ETH,
    PATTERN_BIP44,
    PATTERN_SEP5,
    PATTERN_SEP5_LEDGER_LIVE_LEGACY,
    PATTERN_CASA,
];

const CURVE: &str = "secp256k1";

pub struct Keychain<A: PathSchemaTrait> {
    schemas: Vec<A>,
    curve: &'static str,
}

impl<A: PathSchemaTrait> Keychain<A> {
    pub fn new(schemas: Vec<A>) -> Self {
        let mut instance = Self {
            schemas: schemas,
            curve: CURVE,
        };
        instance
    }
}

impl<A: PathSchemaTrait> KeychainValidator for Keychain<A> {
    fn is_in_keychain(&self, path: &Bip32Path) -> bool {
        self.schemas.iter().any(|schema| schema.matches(path))
    }

    fn verify_path(&self, path: &Bip32Path) -> Result<()> {
        if self.curve.contains("ed25519") && !path.is_hardened() {
            // TODO:  DataError("Non-hardened paths unsupported on Ed25519")
            return Err(Error::DataError);
        }

        // TODO
        // if not safety_checks.is_strict():
        //     return

        if !self.is_in_keychain(path) {
            // TODO: raise ForbiddenKeyPath()
            return Err(Error::DataError);
        }
        Ok(())
    }
}

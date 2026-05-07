use crate::common::COIN;

#[cfg(not(test))]
use alloc::{
    string::{String, ToString},
    vec::Vec,
};
use core::convert::AsRef;
#[cfg(test)]
use std::{
    string::{String, ToString},
    vec::Vec,
};

// https://github.com/bitcoin/bips/blob/master/bip-0044.mediawiki
// The BIP44 pattern, overloaded to be used for ETH accounts, as described above
const PATTERN_BIP44_ETH: &str = "m/44'/coin_type'/0'/0/account";

// BIP-44 for basic (legacy) Bitcoin accounts, and widely used for other currencies:
// https://github.com/bitcoin/bips/blob/master/bip-0044.mediawiki
const PATTERN_BIP44: &str = "m/44'/coin_type'/account'/change/address_index";
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

const HARDENED: u32 = 0x8000_0000;

pub(crate) struct Bip32Path {
    path: Vec<u32>,
}

impl Bip32Path {
    pub fn from_slice(path: &[u32]) -> Self {
        Self {
            path: path.to_vec(),
        }
    }

    pub fn as_slice(&self) -> &[u32] {
        &self.path
    }

    pub fn to_string(&self) -> String {
        if self.path.is_empty() {
            return String::from("m");
        }

        let mut s = String::from("m");
        for segment in &self.path {
            s.push('/');
            if segment & HARDENED != 0 {
                s.push_str(&(segment ^ HARDENED).to_string());
                s.push('\'');
            } else {
                s.push_str(&segment.to_string());
            }
        }
        s
    }

    pub fn get_account_name(&self, coin: &str, pattern: &[&str], slip44_id: u32) -> Option<String> {
        let account_num = self.get_account_num(pattern, slip44_id)?;
        let mut s = String::from(coin);
        s.push_str(" #");
        s.push_str(&account_num.to_string());
        Some(s)
    }

    fn get_account_num(&self, patterns: &[&str], slip44_id: u32) -> Option<u32> {
        for pattern in patterns {
            if let Some(num) = self.get_account_num_single(pattern, slip44_id) {
                return Some(num);
            }
        }
        None
    }

    fn get_account_num_single(&self, pattern: &str, _slip44_id: u32) -> Option<u32> {
        if let Some(account_pos) = pattern.find("/account") {
            let slash_count = pattern[..account_pos].matches('/').count();

            if slash_count >= self.path.len() {
                return None;
            }

            let num = self.path[slash_count];

            if num & HARDENED != 0 {
                Some((num ^ HARDENED) + 1)
            } else {
                Some(num + 1)
            }
        } else {
            None
        }
    }

    pub fn slip44(&self) -> Option<u32> {
        if self.path.len() < 2 {
            return None;
        }

        if self.path[0] == 45 | HARDENED && self.path[1] & HARDENED == 0 {
            return Some(self.path[1]);
        }
        return Some(self.path[1] & !HARDENED);
    }

    pub fn account_and_path(&self) -> (Option<String>, Option<String>) {
        if self.path.len() < 2 {
            return (None, None);
        }

        let slip44_id = self.path[1]; //it depends on the network (ETH vs ETC...)
        let account = self.get_account_name(COIN, &PATTERNS_ADDRESS, slip44_id);
        let path = self.to_string();

        (account, Some(path))
    }
}

impl AsRef<[u32]> for Bip32Path {
    fn as_ref(&self) -> &[u32] {
        &self.path
    }
}

pub fn unharden(item: u32) -> u32 {
    item ^ (item & HARDENED)
}

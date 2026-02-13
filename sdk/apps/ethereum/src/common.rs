use trezor_app_sdk::ui;
use trezor_app_sdk::util;
use trezor_app_sdk::{Error, Result};

extern crate alloc;

use alloc::string::String;
use alloc::string::ToString;

use ufmt::uwrite;

pub(crate) struct Bip32Path {
    pub path: alloc::vec::Vec<u32>,
}

const HARDENED: u32 = 0x8000_0000;

impl Bip32Path {
    pub fn from_slice(path: &[u32]) -> Self {
        Self {
            path: path.to_vec(),
        }
    }

    pub fn length(&self) -> usize {
        self.path.len()
    }

    pub fn to_string(&self) -> alloc::string::String {
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

    pub fn is_hardened(&self) -> bool {
        self.path.iter().all(|segment| segment & HARDENED != 0)
    }

    pub fn as_ref(&self) -> &[u32] {
        &self.path
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
}

pub(crate) fn require_confirm_address(
    address_bytes: &[u8],
    title: Option<&'static str>,
    subtitle: Option<&'static str>,
    verb: Option<&'static str>,
    br_name: Option<&'static str>,
    warning_footer: Option<&'static str>,
) -> Result<()> {
    let address = util::hex_encode(address_bytes);

    let res = ui::confirm_value(title.unwrap_or("Signing address"), address.as_str());
    if matches!(res, Ok(ui::TrezorUiResult::Confirmed)) {
        Ok(())
    } else {
        Err(Error::Cancelled)
    }
}

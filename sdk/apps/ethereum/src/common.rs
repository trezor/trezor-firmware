use crate::{strutil::hex_encode, uformat};
#[cfg(not(test))]
use alloc::string::{String, ToString};
#[cfg(test)]
use std::string::{String, ToString};
use trezor_app_sdk::{Error, Result, ui};

pub(crate) fn require_confirm_address(
    address_bytes: &[u8],
    title: Option<&'static str>,
    _subtitle: Option<&'static str>,
    _verb: Option<&'static str>,
    _br_name: Option<&'static str>,
    _warning_footer: Option<&'static str>,
) -> Result<()> {
    // TODO use all arguments
    let address_hex = uformat!("0x{}", hex_encode(address_bytes).as_str());
    let res = ui::confirm_value(title.unwrap_or("Signing address"), &address_hex);
    if matches!(res, Ok(ui::TrezorUiResult::Confirmed)) {
        Ok(())
    } else {
        Err(Error::Cancelled)
    }
}

pub(crate) fn confirm_signverify(
    _message: &str,
    address: &str,
    verify: bool,
    _path: Option<&str>,
    _account: Option<&str>,
    _chunkify: bool,
) -> Result<()> {
    let address_title = if verify {
        "Verify address"
    } else {
        "Confirm address"
    };

    // TODO implement actual signing logic

    let res = ui::confirm_value(address_title, address);
    if matches!(res, Ok(ui::TrezorUiResult::Confirmed)) {
        Ok(())
    } else {
        Err(Error::Cancelled)
    }
}

pub(crate) fn decode_message(message: &[u8]) -> String {
    match core::str::from_utf8(message) {
        Ok(s) => s.to_string(),
        Err(_) => {
            use crate::strutil::hex_encode;
            uformat!("hex({})", hex_encode(message).as_str())
        }
    }
}

use crate::{strutil::hex_encode, uformat};
#[cfg(not(test))]
use alloc::string::{String, ToString};
#[cfg(test)]
use std::string::{String, ToString};
use trezor_app_sdk::{Error, Result, ui};

pub(crate) fn require_confirm_address(
    address_bytes: &[u8],
    title: Option<&'static str>,
    subtitle: Option<&'static str>,
    description: Option<&'static str>,
    verb: Option<&'static str>,
    br_name: Option<&'static str>,
    warning_footer: Option<&'static str>,
) -> Result<()> {
    let address_hex = uformat!("0x{}", hex_encode(address_bytes).as_str());
    return confirm_address(
        title.unwrap_or("Signing address"),
        &address_hex,
        subtitle,
        description,
        verb,
        warning_footer,
        None,
        br_name,
        Some(8), /* ButtonRequest_SignTx = 8 */
    );
}

pub(crate) fn confirm_signverify(
    _message: &str,
    address: &str,
    verify: bool,
    _path: Option<&str>,
    _account: Option<&str>,
    chunkify: bool,
) -> Result<()> {
    let (address_title, br_name) = if verify {
        ("Verify address", "verify_message")
    } else {
        ("Confirm address", "sign_message")
    };

    // TODO implement actual signing logic

    let res = ui::confirm_value_simple(
        address_title,
        address,
        None,
        br_name,
        None,
        true,
        Some("Continue"),
        None,
        false,
        chunkify,
        false,
        true,
    );
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

pub(crate) fn confirm_address(
    title: &str,
    address: &str,
    subtitle: Option<&str>,
    description: Option<&str>,
    verb: Option<&str>,
    warning_footer: Option<&str>,
    chunkify: Option<bool>,
    br_name: Option<&str>,
    br_code: Option<u32>,
) -> Result<()> {
    if matches!(
        ui::confirm_value_simple(
            title,
            address,
            description,
            br_name.unwrap_or("confirm_address"),
            Some(br_code.unwrap_or(1)), /* ButtonRequest_Other = 1 */
            true,
            verb,
            subtitle,
            false,
            chunkify.unwrap_or(true),
            false,
            false,
        ),
        Ok(ui::TrezorUiResult::Confirmed)
    ) {
        Ok(())
    } else {
        Err(Error::Cancelled)
    }
}

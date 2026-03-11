use crate::{strutil::hex_encode, uformat};
#[cfg(not(test))]
use alloc::{
    string::{String, ToString},
    vec::Vec,
};
#[cfg(test)]
use std::{
    string::{String, ToString},
    vec::Vec,
};
use trezor_app_sdk::{Error, Result, ui};

const LONG_MSG_PAGE_THRESHOLD: usize = 300;

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
    message: &str,
    address: &str,
    verify: bool,
    path: Option<&str>,
    account: Option<&str>,
    chunkify: bool,
) -> Result<()> {
    let (address_title, br_name) = if verify {
        ("Verify address", "verify_message")
    } else {
        ("Signing address", "sign_message")
    };

    let mut items = Vec::with_capacity(3);
    account.map(|a| items.push(("Account", a, true)));
    path.map(|p| items.push(("Derivation path", p, true)));
    let size = uformat!("{} bytes", message.len());
    items.push(("Message size", &size, true));

    loop {
        let res = ui::confirm_value_with_info(
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
            "Information",
            &items,
            true,
        );
        match res {
            Ok(ui::TrezorUiResult::Confirmed) => {
                break;
            }
            Ok(ui::TrezorUiResult::Cancelled) => {
                // Right button aborts action, left goes back to showing address.
                if matches!(
                    ui::show_mismatch("Address mismatch?"),
                    Ok(ui::TrezorUiResult::Confirmed)
                ) {
                    return Err(Error::Cancelled);
                } else {
                    continue;
                }
            }
            _ => {
                // Other results (e.g. Info) are not expected here
                return Err(Error::Cancelled);
            }
        }
    }

    let title = "Confirm message";
    let br_code = 1; /* ButtonRequest_Other = 1 */
    let hold = !verify;
    let result = if message.chars().count() > LONG_MSG_PAGE_THRESHOLD {
        ui::confirm_blob(
            title,
            message,
            None,
            None,
            br_name,
            br_code,
            hold,
            Some("Confirm"),
            None,
            chunkify,
            true,
        )?
    } else {
        ui::confirm_value_simple(
            title,
            message,
            None,
            br_name,
            Some(br_code),
            true,
            None,
            None,
            hold,
            false,
            false,
            true,
        )?
    };
    if matches!(result, ui::TrezorUiResult::Confirmed) {
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
            true,
        ),
        Ok(ui::TrezorUiResult::Confirmed)
    ) {
        Ok(())
    } else {
        Err(Error::Cancelled)
    }
}

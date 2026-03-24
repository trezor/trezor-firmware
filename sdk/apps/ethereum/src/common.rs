use crate::{proto::common::button_request::ButtonRequestType, strutil::hex_encode, uformat};
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
        ButtonRequestType::ButtonRequestSignTx.into(),
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
        let res = ui::interact_with_info_flow(
            |name| {
                ui::confirm_value(
                    address_title,
                    address,
                    None,
                    name,
                    ButtonRequestType::ButtonRequestOther.into(),
                    true,
                    Some("Continue"),
                    None,
                    true,
                    false,
                    chunkify,
                    false,
                    true,
                    false,
                    None,
                )
            },
            |name| {
                ui::show_info_with_cancel(
                    "Information",
                    &items,
                    chunkify,
                    name,
                    ButtonRequestType::ButtonRequestOther.into(),
                )
            },
            br_name,
            None,
            None,
        );

        match res {
            Ok(_) => {
                break;
            }
            Err(_) => {
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
    let br_code = ButtonRequestType::ButtonRequestOther.into();
    let hold = !verify;
    if message.chars().count() > LONG_MSG_PAGE_THRESHOLD {
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
            true,
        )?;
    } else {
        ui::error_if_not_confirmed(ui::confirm_value(
            title,
            message,
            None,
            Some(br_name),
            br_code,
            true,
            None,
            None,
            false,
            hold,
            false,
            false,
            true,
            false,
            None,
        )?)?;
    };
    Ok(())
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
    br_code: i32,
) -> Result<()> {
    if matches!(
        ui::confirm_value(
            title,
            address,
            description,
            Some(br_name.unwrap_or("confirm_address")),
            br_code,
            true,
            verb,
            subtitle,
            false,
            false,
            chunkify.unwrap_or(true),
            false,
            true,
            false,
            warning_footer,
        ),
        Ok(ui::TrezorUiResult::Confirmed)
    ) {
        Ok(())
    } else {
        Err(Error::Cancelled)
    }
}

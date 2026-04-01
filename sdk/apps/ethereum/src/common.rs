use crate::{
    EthereumMessages,
    definitions::{self, Definitions},
    helpers::{Refund, Trade, address_from_bytes, format_ethereum_amount, is_swap},
    paths::Bip32Path,
    payment_request::PaymentRequestVerifier,
    payment_request::parse_amount,
    proto::{
        common::{PaymentRequest, button_request::ButtonRequestType},
        definitions::{EthereumNetworkInfo, EthereumTokenInfo},
        ethereum::{EthereumTxAck, EthereumTxRequest},
    },
    strutil::hex_encode,
    tokens, uformat, wire_request,
};
#[cfg(not(test))]
use alloc::{
    string::{String, ToString},
    vec::Vec,
};
use primitive_types::U256;
#[cfg(test)]
use std::{
    string::{String, ToString},
    vec::Vec,
};
use trezor_app_sdk::{
    Error, Result, info,
    ui::{self, Property, StrExt},
    unwrap,
};

// TODO: This threshold is arbitrary
const LONG_MSG_PAGE_THRESHOLD: usize = 300;

// Known ERC-20 functions
pub const SC_FUNC_SIG_TRANSFER: [u8; 4] = [0xa9, 0x05, 0x9c, 0xbb];
pub const SC_FUNC_SIG_APPROVE: [u8; 4] = [0x09, 0x5e, 0xa7, 0xb3];
pub const SC_FUNC_SIG_STAKE: [u8; 4] = [0x3a, 0x29, 0xdb, 0xae];
pub const SC_FUNC_SIG_UNSTAKE: [u8; 4] = [0x76, 0xec, 0x87, 0x1c];
pub const SC_FUNC_SIG_CLAIM: [u8; 4] = [0x33, 0x98, 0x6f, 0xfa];

// Smart contract 'data' field lengths in bytes
pub const SC_FUNC_SIG_BYTES: usize = 4;
pub const SC_ARGUMENT_BYTES: usize = 32;
pub const SC_ARGUMENT_ADDRESS_BYTES: usize = 20;
pub const SC_FUNC_APPROVE_REVOKE_AMOUNT: u32 = 0;

// Everstake staking

// addresses for pool (stake/unstake) and accounting (claim) operations
pub const ADDRESSES_POOL: [[u8; 20]; 2] = [
    [
        0xAF, 0xA8, 0x48, 0x35, 0x71, 0x54, 0xA6, 0xA6, 0x24, 0x68, 0x6B, 0x34, 0x83, 0x03, 0xEF,
        0x9A, 0x13, 0xF6, 0x32, 0x64,
    ], // Hoodi testnet
    [
        0xD5, 0x23, 0x79, 0x4C, 0x87, 0x9D, 0x9E, 0xC0, 0x28, 0x96, 0x0A, 0x23, 0x1F, 0x86, 0x67,
        0x58, 0xE4, 0x05, 0xBE, 0x34,
    ], // mainnet
];

pub const ADDRESSES_ACCOUNTING: [[u8; 20]; 2] = [
    [
        0x62, 0x40, 0x87, 0xDD, 0x19, 0x04, 0xAB, 0x12, 0x2A, 0x32, 0x87, 0x8C, 0xE9, 0xE9, 0x33,
        0xC7, 0x07, 0x1F, 0x53, 0xB9,
    ], // Hoodi testnet
    [
        0x7A, 0x7F, 0x0B, 0x3C, 0x23, 0xC2, 0x3A, 0x31, 0xCF, 0xCB, 0x0C, 0x44, 0x70, 0x9B, 0xE7,
        0x0D, 0x4D, 0x54, 0x5C, 0x6E,
    ], // mainnet
];

// Approve known addresses
// This should eventually grow into a more comprehensive database and stored in some other way,
// but for now let's just keep a few known addresses here!
const ADDR_UNISWAP_V3_ROUTER: [u8; 20] = [
    0xe5, 0x92, 0x42, 0x7a, 0x0a, 0xec, 0xe9, 0x2d, 0xe3, 0xed, 0xee, 0x1f, 0x18, 0xe0, 0x15, 0x7c,
    0x05, 0x86, 0x15, 0x64,
];
const ADDR_1INCH_V6: [u8; 20] = [
    0x11, 0x11, 0x11, 0x12, 0x54, 0x21, 0xca, 0x6d, 0xc4, 0x52, 0xd2, 0x89, 0x31, 0x42, 0x80, 0xa0,
    0xf8, 0x84, 0x2a, 0x65,
];
const ADDR_LIFI_DIAMOND: [u8; 20] = [
    0x12, 0x31, 0xde, 0xb6, 0xf5, 0x74, 0x9e, 0xf6, 0xce, 0x69, 0x43, 0xa2, 0x75, 0xa1, 0xd3, 0xe7,
    0x48, 0x6f, 0x4e, 0xae,
];

pub const APPROVE_KNOWN_ADDRESSES: [([u8; 20], &str); 3] = [
    (ADDR_UNISWAP_V3_ROUTER, "Uniswap V3 Router"),
    (ADDR_1INCH_V6, "1inch Aggregation Router V6"),
    (ADDR_LIFI_DIAMOND, "LiFI Diamond"),
];

pub fn get_approve_known_address(addr: &[u8]) -> Option<&'static str> {
    APPROVE_KNOWN_ADDRESSES
        .iter()
        .find(|(a, _)| a.as_slice() == addr)
        .map(|(_, name)| *name)
}

pub const COIN: &str = "ETH";

// EIP-7702
pub const EIP_7702_TX_TYPE: u32 = 4;

// EIP-7702
const ADDR_EIP7702_UNISWAP: [u8; 20] = [
    0x00, 0x00, 0x00, 0x00, 0x9b, 0x1d, 0x0a, 0xf2, 0x0d, 0x8c, 0x6d, 0x0a, 0x44, 0xe1, 0x62, 0xd1,
    0x1f, 0x9b, 0x8f, 0x00,
];
const ADDR_EIP7702_ALCHEMY: [u8; 20] = [
    0x69, 0x00, 0x77, 0x02, 0x76, 0x41, 0x79, 0xf1, 0x4f, 0x51, 0xcd, 0xce, 0x75, 0x2f, 0x4f, 0x77,
    0x5d, 0x74, 0xe1, 0x39,
];
const ADDR_EIP7702_AMBIRE: [u8; 20] = [
    0x5a, 0x7f, 0xc1, 0x13, 0x97, 0xe9, 0xa8, 0xad, 0x41, 0xbf, 0x10, 0xbf, 0x13, 0xf2, 0x2b, 0x0a,
    0x63, 0xf9, 0x6f, 0x6d,
];
const ADDR_EIP7702_METAMASK: [u8; 20] = [
    0x63, 0xc0, 0xc1, 0x9a, 0x28, 0x2a, 0x1b, 0x52, 0xb0, 0x7d, 0xd5, 0xa6, 0x5b, 0x58, 0x94, 0x8a,
    0x07, 0xda, 0xe3, 0x2b,
];
const ADDR_EIP7702_EF_AA: [u8; 20] = [
    0x4c, 0xd2, 0x41, 0xe8, 0xd1, 0x51, 0x0e, 0x30, 0xb2, 0x07, 0x63, 0x97, 0xaf, 0xc7, 0x50, 0x8a,
    0xe5, 0x9c, 0x66, 0xc9,
];
const ADDR_EIP7702_LUGANODES: [u8; 20] = [
    0x17, 0xc1, 0x1f, 0xdd, 0xad, 0xac, 0x2b, 0x34, 0x1f, 0x24, 0x55, 0xaf, 0xe9, 0x88, 0xfe, 0xc4,
    0xc3, 0xba, 0x26, 0xe3,
];

const EIP7702_KNOWN_ADDRESSES: [([u8; 20], &str); 6] = [
    (ADDR_EIP7702_UNISWAP, "Uniswap"),
    (ADDR_EIP7702_ALCHEMY, "alchemyplatform"),
    (ADDR_EIP7702_AMBIRE, "AmbireTech"),
    (ADDR_EIP7702_METAMASK, "MetaMask"),
    (ADDR_EIP7702_EF_AA, "Ethereum Foundation AA team"),
    (ADDR_EIP7702_LUGANODES, "Luganodes"),
];

pub fn get_eip_7702_known_address(addr: &[u8]) -> Option<&'static str> {
    EIP7702_KNOWN_ADDRESSES
        .iter()
        .find(|(a, _)| a.as_slice() == addr)
        .map(|(_, name)| *name)
}

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
    account.map(|a| items.push(Property::new("Account", a, true)));
    path.map(|p| items.push(Property::new("Derivation path", p, true)));
    let size = uformat!("{} bytes", message.len());
    items.push(Property::new("Message size", size.as_str(), true));

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
                    ui::show_mismatch(
                        "Address mismatch?",
                        ButtonRequestType::ButtonRequestOther.into()
                    ),
                    Ok(ui::TrezorUiResult::Confirmed)
                ) {
                    return Err(Error::Cancelled);
                } else {
                    continue;
                }
            }
            _ => {
                // todo: implement: Other results (e.g. Info) are not expected here
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

pub fn require_confirm_approve<'a>(
    to_bytes: &'a [u8],
    value: Option<U256>,
    dp: &'a Bip32Path,
    maximum_fee: &'a str,
    fee_info_items: &[Property<'a>],
    chain_id: u64,
    network: &'a EthereumNetworkInfo,
    token: &'a EthereumTokenInfo,
    token_address: &'a [u8],
    chunkify: bool,
) -> Result<()> {
    let recipient_str = get_approve_known_address(to_bytes);
    let recipient_addr = address_from_bytes(to_bytes, Some(network));
    let chain_id_str = uformat!("{} (0x{:x})", chain_id, chain_id);
    let token_address_str = address_from_bytes(token_address, Some(network));
    let total_amount = if let Some(value) = value {
        Some(format_ethereum_amount(value, Some(token), network, false))
    } else {
        None
    };
    let (_, account_path) = dp.account_and_path();

    let is_unknown_token = token == &tokens::unknown_token();
    let is_unknown_network = network == &definitions::unknown_network();

    // info!("value is {}", value);
    info!("recipient address is {}", recipient_addr.as_str());
    info!("to bytes len is {}", to_bytes.len());

    confirm_ethereum_approve(
        &recipient_addr,
        recipient_str,
        is_unknown_token,
        &token_address_str,
        &token.symbol,
        is_unknown_network,
        &chain_id_str,
        &network.name,
        value == Some(U256::from(SC_FUNC_APPROVE_REVOKE_AMOUNT)),
        total_amount.as_deref(),
        account_path.as_deref(),
        maximum_fee,
        fee_info_items,
        chunkify,
    )?;
    Ok(())
}

fn confirm_ethereum_approve<'a>(
    recipient_addr: &'a str,
    recipient_str: Option<&'a str>,
    is_unknown_token: bool,
    token_address: &'a str,
    token_symbol: &'a str,
    is_unknown_network: bool,
    chain_id: &'a str,
    network_name: &'a str,
    is_revoke: bool,
    total_amount: Option<&'a str>,
    account_path: Option<&'a str>,
    maximum_fee: &'a str,
    fee_info_items: &[Property<'a>],
    chunkify: bool,
) -> Result<()> {
    let br_name = "confirm_ethereum_approve";
    let br_code = ButtonRequestType::ButtonRequestOther.into();
    info!("is revoke is {}", is_revoke);
    let (title, action) = if is_revoke {
        (
            "Token revocation",
            "Review details to revoke token approval.",
        )
    } else {
        (
            "Token approval",
            "Review details to approve token spending.",
        )
    };

    ui::error_if_not_confirmed(ui::confirm_action(
        title,
        action,
        false,
        Some("Continue"),
        Some(br_name),
        ButtonRequestType::ButtonRequestOther.into(),
    )?)?;

    let subtitle = if is_revoke {
        "Revoke from"
    } else {
        "Approve to"
    };

    if let Some(recipient_str) = recipient_str {
        info!("recipient str is {}", recipient_str);
        ui::interact_with_info_flow(
            |name| {
                ui::confirm_with_info(
                    title,
                    Some(subtitle),
                    &[StrExt::new(recipient_str, true)],
                    "Continue",
                    "Provider contract address",
                    name,
                    br_code,
                )
            },
            |name| {
                ui::show_info_with_cancel(
                    title,
                    &[Property::new("", recipient_addr, true)],
                    chunkify,
                    name,
                    br_code,
                )
            },
            br_name,
            None,
            None,
        )?;
    } else {
        info!("recipient str is None, showing address {}", recipient_addr);
        ui::error_if_not_confirmed(ui::confirm_value(
            title,
            recipient_addr,
            None,
            Some(br_name),
            br_code,
            true,
            Some("Continue"),
            Some(subtitle),
            false,
            false,
            chunkify,
            false,
            true,
            false,
            None,
        )?)?;
    };

    if total_amount.is_none() {
        let content = uformat!("Approving unlimited amount of {}", token_symbol);
        ui::show_warning(
            "Important",
            &content,
            "Continue anyway",
            Some(br_name),
            ButtonRequestType::ButtonRequestWarning.into(),
            true,
            true,
        )?;
    }

    if is_unknown_token {
        ui::error_if_not_confirmed(ui::confirm_value(
            "Send",
            token_address,
            None,
            Some(br_name),
            ButtonRequestType::ButtonRequestOther.into(),
            true,
            None,
            Some("Token contract address"),
            false,
            false,
            chunkify,
            false,
            true,
            false,
            None,
        )?)?;
    }

    if is_unknown_network {
        ui::error_if_not_confirmed(ui::confirm_value(
            title,
            chain_id,
            Some("Chain ID"),
            Some(br_name),
            ButtonRequestType::ButtonRequestOther.into(),
            true,
            None,
            None,
            false,
            false,
            false,
            false,
            true,
            false,
            None,
        )?)?;
    }

    let mut props = Vec::with_capacity(2);
    if is_revoke {
        props.push(Property::new("Token", token_symbol, true));
    } else {
        props.push(Property::new(
            "Amount allowance",
            total_amount.unwrap_or("Unlimited"),
            false,
        ));
    }
    if !is_unknown_network {
        props.push(Property::new("Chain", network_name, false));
    }

    ui::error_if_not_confirmed(ui::confirm_properties(
        title,
        &props,
        None,
        Some("Continue"),
        false,
        Some(br_name),
        ButtonRequestType::ButtonRequestOther.into(),
    )?)?;

    let account_item = account_path.map(|p| [Property::new("Derivation path", p, true)]);

    ui::error_if_not_confirmed(ui::confirm_summary(
        Some(title),
        None,
        None,
        maximum_fee,
        "Maximum fee",
        None,
        account_item.as_ref().map(|a| a.as_slice()),
        Some("Fee info"),
        Some(fee_info_items),
        false,
        Some("confirm_total"),
        ButtonRequestType::ButtonRequestOther.into(),
    )?)?;

    Ok(())
}

pub fn require_confirm_claim<'a>(
    address_bytes: &'a [u8],
    dp: &'a Bip32Path,
    maximum_fee: &'a str,
    fee_info_items: &'a [Property<'a>],
    network: &'a EthereumNetworkInfo,
) -> Result<()> {
    let addr_str = address_from_bytes(address_bytes, Some(network));
    let (account, account_path) = dp.account_and_path();

    confirm_ethereum_staking_tx(
        "Claim",
        "Claim ETH from Everstake?",
        "Claim",
        "",
        account.as_deref(),
        account_path.as_deref(),
        maximum_fee,
        &addr_str,
        "Claim address",
        fee_info_items,
        None,
        None,
    )?;

    Ok(())
}

fn confirm_ethereum_staking_tx<'a>(
    title: &'a str,
    intro_question: &'a str,
    verb: &'a str,
    total_amount: &'a str,
    account: Option<&'a str>,
    account_path: Option<&'a str>,
    maximum_fee: &'a str,
    address: &'a str,
    address_title: &'a str,
    info_items: &[Property<'a>],
    br_name: Option<&'a str>,
    br_code: Option<i32>,
) -> Result<()> {
    assert!(verb == "Stake" || verb == "Unstake" || verb == "Claim");

    let br_name = br_name.unwrap_or("confirm_ethereum_staking_tx");
    let br_code = br_code.unwrap_or(ButtonRequestType::ButtonRequestSignTx.into());

    let mut menu_items = Vec::with_capacity(2);
    let props = [Property::new("", address, true)];
    menu_items.push(ui::Details::new(
        address_title,
        &props,
        None,
        None,
        ButtonRequestType::ButtonRequestOther.into(),
    ));

    let account_properties = get_account_info_items(account, account_path);
    if !account_properties.is_empty() {
        menu_items.push(ui::Details::new(
            "Account info",
            &account_properties,
            None,
            Some("Send from"),
            ButtonRequestType::ButtonRequestOther.into(),
        ));
    };

    let amount_label = if verb == "Claim" {
        None
    } else {
        Some("Amount")
    };

    let menu = ui::Menu::new(menu_items.as_slice(), Some(ui::Cancel::new("Cancel sign")));

    let steps: [&dyn Fn() -> ui::UiResult; 2] = [
        &|| {
            ui::interact_with_menu_flow(
                |name| {
                    ui::confirm_value(
                        verb,
                        intro_question,
                        None,
                        name,
                        ButtonRequestType::ButtonRequestSignTx.into(),
                        false,
                        None,
                        None,
                        false,
                        false,
                        false,
                        false,
                        false,
                        true,
                        None,
                    )
                },
                &menu,
                Some(br_name),
            )
        },
        &|| {
            ui::confirm_summary(
                Some(title),
                Some(total_amount),
                amount_label,
                maximum_fee,
                "Maximum fee",
                None,
                None,
                Some("Fee info"),
                Some(info_items),
                true,
                Some("confirm_total"),
                br_code,
            )
        },
    ];
    ui::error_if_not_confirmed(ui::confirm_linear_flow(&steps)?)?;

    Ok(())
}

pub fn require_confirm_payment_request<'a>(
    provider_address: &'a str,
    verified_payment_req: &'a PaymentRequest,
    dp: &'a Bip32Path,
    maximum_fee: &'a str,
    fee_info_items: &'a [Property<'a>],
    chain_id: u64,
    network: &'a EthereumNetworkInfo,
    token: Option<&'a EthereumTokenInfo>,
    token_address: &'a str,
) -> Result<()> {
    info!("formatting total amount for display");
    let total_amount = format_ethereum_amount(
        parse_amount(unwrap!(verified_payment_req.amount.as_deref()))?,
        token,
        network,
        false,
    );
    info!("total amount is {}", total_amount.as_str());

    let mut texts = Vec::new();
    let mut refunds = Vec::new();
    let mut trades = Vec::new();

    for memo in &verified_payment_req.memos {
        if let Some(text_memo) = &memo.text_memo {
            texts.push((None, text_memo.text.as_str()));
        } else if let Some(text_details_memo) = &memo.text_details_memo {
            texts.push((
                Some(text_details_memo.title.as_str()),
                text_details_memo.text.as_str(),
            ));
        } else if let Some(refund_memo) = &memo.refund_memo {
            let (refund_account, refund_account_path) = dp.account_and_path();
            refunds.push(Refund::new(
                &refund_memo.address,
                refund_account.as_deref(),
                refund_account_path.as_deref(),
            )?);
        } else if let Some(coin_purchase_memo) = &memo.coin_purchase_memo {
            let (coin_purchase_account, coin_purchase_account_path) = dp.account_and_path();
            trades.push(Trade::new(
                Some(&uformat!("- {}", total_amount.as_str())),
                &uformat!("+ {}", coin_purchase_memo.amount.as_str()),
                &coin_purchase_memo.address,
                coin_purchase_account.as_deref(),
                coin_purchase_account_path.as_deref(),
            )?);
        } else {
            // TODO: proper error type: DataError("Unrecognized memo type in payment request.")
            return Err(Error::DataError);
        }
    }

    info!("memos finished");

    let (account, account_path) = dp.account_and_path();
    let mut account_items = Vec::with_capacity(3);
    if let Some(ref account) = account {
        account_items.push(Property::new("Account", account.as_str(), true));
    }
    if let Some(ref account_path) = account_path {
        account_items.push(Property::new(
            "Derivation path",
            account_path.as_str(),
            true,
        ));
    }
    let chain_id_str = uformat!("{} ({})", network.name.as_str(), chain_id);
    if chain_id != 0 {
        account_items.push(Property::new("Chain ID", chain_id_str.as_str(), true));
    }
    info!("confirming payment request");

    confirm_payment_request(
        verified_payment_req.recipient_name.as_str(),
        Some(&provider_address),
        texts.as_slice(),
        &refunds,
        &trades,
        &account_items,
        Some(maximum_fee),
        Some(fee_info_items),
        Some(&[("Token contract".into(), token_address.into())]),
    )?;

    Ok(())
}

fn confirm_payment_request<'a>(
    recipient_name: &'a str,
    recipient_address: Option<&'a str>,
    texts: &[(Option<&'a str>, &'a str)],
    refunds: &[Refund],
    trades: &[Trade],
    account_items: &[Property<'a>],
    transaction_fee: Option<&'a str>,
    fee_info_items: Option<&[Property<'a>]>,
    extra_menu_items: Option<&[(&'a str, &'a str)]>,
) -> Result<()> {
    let (title, summary_title) = if is_swap(trades)? {
        ("Swap", "Swap")
    } else {
        ("Confirm", "Summary")
    };

    for (text_title, text) in texts {
        info!("confirming text: {}", text);
        ui::error_if_not_confirmed(ui::confirm_value(
            text_title.unwrap_or(title),
            text,
            None,
            Some("confirm_payment_request"),
            ButtonRequestType::ButtonRequestOther.into(),
            true,
            Some("Confirm"),
            None,
            false,
            false,
            false,
            false,
            false,
            false,
            None,
        )?)?;
    }

    let mut menu_items = Vec::new();

    let props;
    if let Some(recipient_address) = recipient_address {
        props = [Property::new("", recipient_address, true)];
        menu_items.push(ui::Details::new(
            "Provider address",
            &props,
            None,
            None,
            ButtonRequestType::ButtonRequestOther.into(),
        ));
    }

    let mut refund_account_infos: Vec<Vec<Property>> = Vec::with_capacity(refunds.len());
    for refund in refunds {
        let mut refund_account_info = Vec::with_capacity(3);
        refund_account_info.push(Property::new("", refund.address.as_str(), false));

        if let Some(ref refund_account) = refund.account {
            refund_account_info.push(Property::new("Account", refund_account.as_str(), true));
        }

        if let Some(ref refund_account_path) = refund.account_path {
            refund_account_info.push(Property::new(
                "Derivation path",
                refund_account_path.as_str(),
                true,
            ));
        }

        refund_account_infos.push(refund_account_info);
    }

    for refund_account_info in &refund_account_infos {
        menu_items.push(ui::Details::new(
            "Refund address",
            refund_account_info.as_slice(),
            None,
            None,
            ButtonRequestType::ButtonRequestOther.into(),
        ));
    }

    let menu = ui::Menu::new(menu_items.as_slice(), Some(ui::Cancel::new("Cancel sign")));

    let mut back_from_confirm_trade;
    loop {
        // back_from_confirm_trade = false;
        ui::error_if_not_confirmed(ui::interact_with_menu_flow(
            |name| {
                ui::confirm_value(
                    title,
                    recipient_name,
                    None,
                    name,
                    ButtonRequestType::ButtonRequestOther.into(),
                    true,
                    Some("Continue"),
                    Some("Provider"),
                    false,
                    false,
                    false,
                    false,
                    false,
                    true,
                    None,
                )
            },
            &menu,
            Some("confirm_payment_request"),
        )?)?;

        loop {
            back_from_confirm_trade = false;

            // HACK: if we have multiple trades to confirm, we disable the back button
            // to simplify the mechanism we use here to handle it.
            // In practice, this should never happen, since normally there is only one trade in a transaction,
            // but in theory it can (since SLIP-24 supports multiple CoinPurchaseMemos...)
            let can_go_back_from_trade = trades.len() == 1;

            for trade in trades {
                if matches!(
                    trade_flow(
                        title,
                        "Assets",
                        trade,
                        extra_menu_items,
                        can_go_back_from_trade,
                    )?,
                    ui::TrezorUiResult::Back
                ) {
                    back_from_confirm_trade = true;
                    break;
                }
            }

            if back_from_confirm_trade {
                break;
            }

            if let Some(transaction_fee) = transaction_fee {
                if matches!(
                    ui::confirm_summary(
                        Some(summary_title),
                        None,
                        None,
                        transaction_fee,
                        "Transaction fee",
                        None,
                        Some(account_items),
                        Some("Fee info"),
                        fee_info_items,
                        true,
                        Some("confirm_payment_request"),
                        ButtonRequestType::ButtonRequestSignTx.into(),
                    )?,
                    ui::TrezorUiResult::Back
                ) {
                    continue;
                } else {
                    break;
                }
            } else {
                break;
            }
        }
        if back_from_confirm_trade {
            continue;
        } else {
            break;
        }
    }

    Ok(())
}

pub fn get_account_info_items<'a>(
    account: Option<&'a str>,
    account_path: Option<&'a str>,
) -> Vec<Property<'a>> {
    let mut items = Vec::with_capacity(2);
    account.map(|acc| items.push(Property::new("Account", acc, false)));
    account_path.map(|path| items.push(Property::new("Derivation path", path, false)));

    items
}

pub fn require_confirm_other_data(data: &[u8], data_total: u32) -> Result<()> {
    let description = uformat!("Size: {} bytes", data_total);
    let subtitle = uformat!("All input data ({} bytes)", data_total);
    let data_str = hex_encode(data);
    info!(
        "confirming other data with description {}, subtitle {}, and data_str {}",
        description.as_str(),
        subtitle.as_str(),
        data_str.as_str()
    );
    ui::error_if_not_confirmed(ui::confirm_blob(
        "Input data",
        &data_str,
        Some(&description),
        Some(&subtitle),
        "confirm_data",
        ButtonRequestType::ButtonRequestSignTx.into(),
        false,
        Some("Confirm"),
        Some("Cancel sign"),
        false,
        true,
        true,
    )?)?;
    Ok(())
}

pub fn require_confirm_stake<'a>(
    address_bytes: &[u8],
    value: U256,
    dp: &'a Bip32Path,
    maximum_fee: &'a str,
    fee_info_items: &'a [Property<'a>],
    network: &'a EthereumNetworkInfo,
) -> Result<()> {
    let address_str = address_from_bytes(address_bytes, Some(network));
    let total_amount = format_ethereum_amount(value, None, network, false);
    let (account, account_path) = dp.account_and_path();

    confirm_ethereum_staking_tx(
        "Stake",
        "Stake ETH on Everstake?",
        "Stake",
        &total_amount,
        account.as_deref(),
        account_path.as_deref(),
        maximum_fee,
        &address_str,
        "Stake address",
        fee_info_items,
        None,
        None,
    )?;

    Ok(())
}

pub fn require_confirm_tx<'a>(
    recipient: Option<&'a str>,
    value: U256,
    dp: &'a Bip32Path,
    maximum_fee: &'a str,
    fee_info_items: &'a [Property<'a>],
    network: &'a EthereumNetworkInfo,
    token: Option<&'a EthereumTokenInfo>,
    is_send: bool,
    chunkify: bool,
) -> Result<()> {
    let total_amount = format_ethereum_amount(value, token, network, false);
    let (account, account_path) = dp.account_and_path();

    confirm_ethereum_tx(
        recipient,
        &total_amount,
        account.as_deref(),
        account_path.as_deref(),
        maximum_fee,
        fee_info_items,
        is_send,
        None,
        None,
        chunkify,
    )?;
    Ok(())
}

fn confirm_ethereum_tx<'a>(
    recipient: Option<&'a str>,
    total_amount: &str,
    account: Option<&'a str>,
    account_path: Option<&'a str>,
    maximum_fee: &str,
    fee_info_items: &[Property<'a>],
    is_send: bool,
    br_name: Option<&'a str>,
    br_code: Option<i32>,
    chunkify: bool,
) -> Result<()> {
    let br_name = br_name.unwrap_or("confirm_total");
    let br_code = br_code.unwrap_or(ButtonRequestType::ButtonRequestSignTx.into());

    let subtitle = if !is_send && recipient.is_none() {
        None
    } else if is_send {
        Some("Recipient")
    } else {
        Some("Interaction contract address")
    };
    let title = "Send";

    let account_properties = get_account_info_items(account, account_path);
    let menu_items = &[ui::Details::new(
        "Account info",
        &account_properties,
        None,
        Some("Send from"),
        ButtonRequestType::ButtonRequestOther.into(),
    )];

    let menu = ui::Menu::new(menu_items, Some(ui::Cancel::new("Cancel sign")));

    let steps: [&dyn Fn() -> ui::UiResult; 2] = [
        &|| {
            ui::interact_with_menu_flow(
                |name| {
                    ui::confirm_value(
                        title,
                        recipient.unwrap_or("New contract will be deployed"),
                        None,
                        name,
                        br_code,
                        recipient.is_some(),
                        Some("Continue"),
                        subtitle,
                        false,
                        false,
                        if recipient.is_some() { chunkify } else { false },
                        false,
                        false,
                        true,
                        None,
                    )
                },
                &menu,
                Some("confirm_output"),
            )
        },
        &|| {
            ui::confirm_summary(
                Some(title),
                Some(total_amount),
                Some("Amount"),
                maximum_fee,
                "Maximum fee",
                None,
                None,
                Some("Fee info"),
                Some(fee_info_items),
                true,
                Some(br_name),
                br_code,
            )
        },
    ];

    ui::error_if_not_confirmed(ui::confirm_linear_flow(&steps)?)?;

    Ok(())
}

pub fn require_confirm_unstake<'a>(
    address_bytes: &'a [u8],
    value: U256,
    dp: &'a Bip32Path,
    maximum_fee: &'a str,
    fee_info_items: &'a [Property<'a>],
    network: &'a EthereumNetworkInfo,
) -> Result<()> {
    let address_str = address_from_bytes(address_bytes, Some(network));
    let total_amount = format_ethereum_amount(value, None, network, false);
    let (account, account_path) = dp.account_and_path();

    confirm_ethereum_staking_tx(
        "Unstake",
        "Unstake ETH from Everstake?",
        "Unstake",
        &total_amount,
        account.as_deref(),
        account_path.as_deref(),
        maximum_fee,
        &address_str,
        "Stake address",
        fee_info_items,
        None,
        None,
    )?;

    Ok(())
}

fn trade_flow(
    title: &str,
    subtitle: &str,
    trade: &Trade,
    extra_menu_items: Option<&[(&str, &str)]>,
    back_button: bool,
) -> ui::UiResult {
    let mut account_properties = Vec::with_capacity(3);
    account_properties.push(Property::new("", trade.address.as_str(), true));
    if let Some(ref account) = trade.account {
        account_properties.push(Property::new("Account", account.as_str(), true));
    }
    if let Some(ref account_path) = trade.account_path {
        account_properties.push(Property::new(
            "Derivation path",
            account_path.as_str(),
            true,
        ));
    }

    let mut menu_items = Vec::new();
    menu_items.push(ui::Details::new(
        "Receive address",
        &account_properties,
        None,
        Some("Send from"),
        ButtonRequestType::ButtonRequestOther.into(),
    ));

    let extra_props: Option<Vec<[Property; 1]>> = extra_menu_items.map(|items| {
        items
            .iter()
            .map(|(_, value)| [Property::new(*value, "", false)])
            .collect()
    });

    if let (Some(extra_menu_items), Some(extra_props)) = (extra_menu_items, extra_props.as_ref()) {
        for ((label, _), props) in extra_menu_items.iter().zip(extra_props.iter()) {
            menu_items.push(ui::Details::new(
                label,
                props,
                None,
                None,
                ButtonRequestType::ButtonRequestOther.into(),
            ));
        }
    }

    let menu = ui::Menu::new(&menu_items, Some(ui::Cancel::new("Cancel sign")));

    ui::interact_with_menu_flow(
        |name| {
            ui::confirm_trade(
                title,
                subtitle,
                &trade.buy_amount,
                trade.sell_amount.as_deref(),
                back_button,
                name,
                ButtonRequestType::ButtonRequestOther.into(),
            )
        },
        &menu,
        Some("confirm_trade"),
    )
}

pub fn send_request_chunk(data_left: u32) -> Result<EthereumTxAck> {
    let req_size = core::cmp::min(data_left, 1024);
    info!(
        "requesting data chunk with {} bytes left with {} bytes",
        data_left, req_size
    );

    let mut req = EthereumTxRequest::default();
    req.data_length = Some(core::cmp::min(data_left, 1024) as u32);

    let resp: EthereumTxAck = wire_request(&req, EthereumMessages::TxRequest)?;
    info!("received data chunk response");

    Ok(resp)
}

pub fn handle_staking_tx_claim<'a>(
    data: &'a [u8],
    dp: &'a Bip32Path,
    staking_address: &'a [u8],
    maximum_fee: &'a str,
    fee_items: &'a [Property<'a>],
    network: &'a EthereumNetworkInfo,
) -> Result<()> {
    // claim has no args

    if data.len() != 0 {
        return Err(Error::DataError);
    }

    require_confirm_claim(staking_address, dp, maximum_fee, fee_items, network)?;

    Ok(())
}

pub fn handle_staking_tx_stake<'a>(
    data: &'a [u8],
    dp: &'a Bip32Path,
    value: &'a [u8],
    network: &'a EthereumNetworkInfo,
    address_bytes: &'a [u8],
    maximum_fee: &'a str,
    fee_items: &'a [Property<'a>],
) -> Result<()> {
    // stake args:
    // - arg0: uint64, source (1 for Trezor)

    if data.len() != SC_ARGUMENT_BYTES {
        // TODO: proper error type: ValueError: wrong number of arguments for stake (should be 1)
        return Err(Error::DataError);
    }

    assert!(value.len() <= 32);
    let value = U256::from_big_endian(value);

    require_confirm_stake(address_bytes, value, dp, maximum_fee, fee_items, network)?;

    Ok(())
}

pub fn handle_staking_tx_unstake<'a>(
    data: &'a [u8],
    dp: &'a Bip32Path,
    network: &'a EthereumNetworkInfo,
    address_bytes: &'a [u8],
    maximum_fee: &'a str,
    fee_items: &'a [Property<'a>],
) -> Result<()> {
    // unstake args:
    // - arg0: uint256, value
    // - arg1: uint16, isAllowedInterchange (bool)
    // - arg2: uint64, source (1 for Trezor)

    if data.len() != 3 * SC_ARGUMENT_BYTES {
        // TODO: proper error type: ValueError: wrong number of arguments for unstake (should be 3)
        return Err(Error::DataError);
    }

    // parse arg0: uint256, value (only lower 16 bytes fit in u128)
    let arg0 = &data[..SC_ARGUMENT_BYTES];
    let value = U256::from_big_endian(arg0);

    // skip arg1 and arg2

    require_confirm_unstake(address_bytes, value, dp, maximum_fee, fee_items, network)?;

    Ok(())
}

/// Runs confirmation for ETH staking approval for staking related transactions.
pub fn run_staking_approver<'a>(
    dp: &'a Bip32Path,
    data_initial_chunk: &'a [u8],
    value: &'a [u8],
    network: &'a EthereumNetworkInfo,
    address_bytes: &'a [u8],
    maximum_fee: &'a str,
    fee_items: &'a [Property<'a>],
) -> Result<bool> {
    if data_initial_chunk.len() < SC_FUNC_SIG_BYTES {
        return Ok(false);
    }

    let func_sig = &data_initial_chunk[..SC_FUNC_SIG_BYTES];
    let data = &data_initial_chunk[SC_FUNC_SIG_BYTES..];
    if ADDRESSES_POOL
        .iter()
        .any(|addr| addr.as_slice() == address_bytes)
    {
        if func_sig == &SC_FUNC_SIG_STAKE {
            handle_staking_tx_stake(
                data,
                &dp,
                value,
                network,
                address_bytes,
                maximum_fee,
                fee_items,
            )?;
            return Ok(true);
        } else if func_sig == &SC_FUNC_SIG_UNSTAKE {
            handle_staking_tx_unstake(data, &dp, network, address_bytes, maximum_fee, fee_items)?;
            return Ok(true);
        }
    }

    if ADDRESSES_ACCOUNTING
        .iter()
        .any(|addr| addr.as_slice() == address_bytes)
    {
        if func_sig == &SC_FUNC_SIG_CLAIM {
            handle_staking_tx_claim(data, &dp, address_bytes, maximum_fee, fee_items, network)?;
            return Ok(true);
        }
    }

    Ok(false)
}

pub fn check_common_fields(
    data_length: u32,
    data_initial_chunk: &[u8],
    to: &str,
    chain_id: u64,
) -> Result<()> {
    info!("checking data length and initial chunk");
    if data_length > 0 {
        // TODO: proper error type: DataError("Data length provided, but no initial chunk")
        if data_initial_chunk.is_empty() {
            info!("Data length provided, but no initial chunk");
            return Err(Error::DataError);
        }

        // Our encoding only supports transactions up to 2^24 bytes. To
        // prevent exceeding the limit we use a stricter limit on data length.
        if data_length > 16_000_000 {
            // TODO: proper error type: DataError("Data length exceeds limit")
            info!("Data length exceeds limit");
            return Err(Error::DataError);
        }

        if data_initial_chunk.len() > data_length as usize {
            // TODO: proper error type: DataError("Invalid size of initial chunk")
            info!("Invalid size of initial chunk");
            return Err(Error::DataError);
        }
    }

    if !matches!(to.len(), 0 | 40 | 42) {
        // TODO: proper error type: DataError("Invalid recipient address")
        info!("Invalid recipient address");
        return Err(Error::DataError);
    }

    if to.is_empty() && data_length == 0 {
        // sending transaction to address 0 (contract creation) without a data field
        // TODO: proper error type: DataError("Contract creation without data")
        info!("Contract creation without data");
        return Err(Error::DataError);
    }

    info!("checking chain id");
    if chain_id == 0 {
        // TODO: proper error type: DataError("Chain ID out of bounds")
        info!("Chain ID out of bounds");
        return Err(Error::DataError);
    }

    Ok(())
}

pub fn confirm_tx_data<'a>(
    dp: &'a Bip32Path,
    data_initial_chunk: &'a [u8],
    data_length: u32,
    value: &'a [u8],
    to: &'a str,
    chain_id: u64,
    chunkify: Option<bool>,
    definitions: &'a Definitions,
    tx_type: Option<u32>,
    address_bytes: &'a [u8],
    maximum_fee: &'a str,
    fee_items: &'a [Property<'a>],
    payment_req: Option<&'a PaymentRequest>,
    payment_req_verifier: Option<PaymentRequestVerifier>,
) -> Result<()> {
    if true
        == run_staking_approver(
            &dp,
            data_initial_chunk,
            value,
            &definitions.network(),
            address_bytes,
            maximum_fee,
            fee_items,
        )?
    {
        return Ok(());
    }

    info!("checking if transaction is a known contract call");
    if matches!(tx_type, Some(EIP_7702_TX_TYPE)) {
        // we have already made sure that the address is a known address
        // as part of the initial validation

        info!("authorizing smart account");

        ui::error_if_not_confirmed(ui::confirm_value(
            "Smart accounts",
            unwrap!(get_eip_7702_known_address(&address_bytes)),
            Some("Authorize the following contract as an EIP-7702 on your account?"),
            Some("confirm_provider"),
            ButtonRequestType::ButtonRequestOther.into(),
            true,
            None,
            None,
            false,
            false,
            false,
            false,
            false,
            false,
            None,
        )?)?;
    }

    info!("handling known contract calls");
    let (token, token_address, func_sig, recipient, value) = handle_known_contract_calls(
        data_initial_chunk,
        data_length,
        to,
        value,
        definitions,
        address_bytes,
    )?;

    info!("recipient len is {}", recipient.len());

    info!(
        "func sig len is {}",
        func_sig.as_ref().map(|s| s.len()).unwrap_or(0)
    );
    let is_approve = func_sig.as_deref() == Some(SC_FUNC_SIG_APPROVE.as_slice());
    let is_unknown_token = &token == &Some(tokens::unknown_token());

    if is_unknown_token {
        let title = String::from(if is_approve {
            if matches!(value, Some(v) if v == U256::from(SC_FUNC_APPROVE_REVOKE_AMOUNT)) {
                "Token revocation"
            } else {
                "Token approval"
            }
        } else {
            "Send"
        });

        info!(
            "unknown token contract address: showing warning with title {}",
            title.as_str()
        );

        ui::error_if_not_confirmed(ui::show_danger(
            "Important",
            "Unknown token contract address. Continue only if you know what you are doing!",
            Some("unknown_contract_warning"),
            ButtonRequestType::ButtonRequestWarning.into(),
            Some("Cancel sign"),
            Some(&title),
        )?)?;

        if !is_approve {
            // For unknown tokens we also show the token address immediately after the warning
            // except in the case of the "approve" flow which shows the token address later on!
            require_confirm_address(
                address_bytes,
                Some("Send"),
                Some("Token contract address"),
                None,
                Some("Continue"),
                Some("unknown_token"),
                Some("Unknown token contract address."),
            )?
        }
    }

    if is_approve {
        info!("handling approve flow");

        if token.is_none() || token_address.is_none() {
            // TODO: proper error type
            return Err(Error::DataError);
        }

        info!(
            "token address len is {:?}",
            token_address.as_deref().map(|a| a.len())
        );

        if payment_req_verifier.is_some() {
            // TODO: proper error type: DataError("Payment Requests not supported for the APPROVE call")
            return Err(Error::DataError);
        }

        require_confirm_approve(
            &recipient,
            value,
            &dp,
            maximum_fee,
            fee_items,
            chain_id,
            &definitions.network(),
            &token.unwrap(),
            &token_address.unwrap(),
            chunkify.unwrap_or(false),
        )?;
    } else {
        info!("handling regular transaction flow");
        assert!(value.is_some());

        let recipient_str = if !recipient.is_empty() {
            info!("recipient is not empty, treating as regular transaction");
            Some(address_from_bytes(&recipient, Some(definitions.network())))
        } else {
            info!("recipient is empty, treating as contract creation");
            None
        };
        let token_address_str = address_from_bytes(address_bytes, Some(definitions.network()));
        let is_contract_interaction = token.is_none() && data_length > 0;

        info!("is contract interaction: {}", is_contract_interaction);
        info!("data_length: {}", data_length);

        if let Some(mut payment_req_verifier) = payment_req_verifier {
            info!("handling payment request flow");
            if is_contract_interaction {
                // TODO: proper error type: DataError("Payment Requests don't support contract interactions")
                info!("payment requests don't support contract interactions");
                return Err(Error::DataError);
            }

            // If a payment_req_verifier is provided, then msg.payment_req must have been set.
            if payment_req.is_none() || recipient_str.is_none() {
                // TODO: proper error type
                info!(
                    "invalid payment request: recipient must be empty and payment_req must be provided"
                );
                return Err(Error::DataError);
            }

            payment_req_verifier.add_output(
                unwrap!(value).into(),
                unwrap!(recipient_str.as_deref()),
                None,
            )?;
            info!("verifying payment request");
            payment_req_verifier.verify()?;

            require_confirm_payment_request(
                unwrap!(recipient_str.as_deref()),
                payment_req.as_ref().unwrap(),
                &dp,
                maximum_fee,
                fee_items,
                chain_id,
                definitions.network(),
                token.as_ref(),
                &token_address_str,
            )?;
        } else {
            if is_contract_interaction {
                require_confirm_other_data(data_initial_chunk, data_length)?;
            };

            require_confirm_tx(
                recipient_str.as_deref(),
                unwrap!(value),
                &dp,
                maximum_fee,
                fee_items,
                definitions.network(),
                token.as_ref(),
                !is_contract_interaction && tx_type != Some(EIP_7702_TX_TYPE),
                chunkify.unwrap_or(false),
            )?;
        };
    };

    Ok(())
}

fn handle_known_contract_calls(
    data_initial_chunk: &[u8],
    data_length: u32,
    to: &str,
    value_bytes: &[u8],
    definitions: &Definitions,
    address_bytes: &[u8],
) -> Result<(
    Option<EthereumTokenInfo>,
    Option<Vec<u8>>,
    Option<Vec<u8>>,
    Vec<u8>,
    Option<U256>,
)> {
    let mut token = None;
    let mut token_address = None;
    let mut recipient = Vec::from(address_bytes);

    // TODO: better implement parsing int value from bytes
    assert!(value_bytes.len() <= 32);
    let mut value = Some(U256::from_big_endian(value_bytes));

    let mut offset = 0;
    let mut remaining = data_initial_chunk.len();

    if remaining < SC_FUNC_SIG_BYTES {
        info!("data too short");
        return Ok((token, token_address, None, recipient, value));
    }

    let mut func_sig = Some(Vec::from(
        &data_initial_chunk[offset..(offset + SC_FUNC_SIG_BYTES)],
    ));
    offset += SC_FUNC_SIG_BYTES;
    remaining -= SC_FUNC_SIG_BYTES;

    if matches!(to.len(), 40 | 42)
        && value_bytes.len() == 0
        && data_length == 68
        && data_initial_chunk.len() == 68
        && (matches!(func_sig.as_deref(), Some(sig) if sig == &SC_FUNC_SIG_TRANSFER)
            || matches!( func_sig.as_deref(), Some(sig) if sig == &SC_FUNC_SIG_APPROVE))
    {
        // The two functions happen to have the exact same parameters, so we treat them together.
        // This will need to be made into a more generic solution eventually.
        // arg0: address, Address, 20 bytes (left padded with zeroes)
        // arg1: value, uint256, 32 bytes

        if remaining < SC_ARGUMENT_BYTES * 2 {
            return Ok((token, token_address, None, recipient, value));
        }

        let arg0 = &data_initial_chunk[offset..(offset + SC_ARGUMENT_BYTES)];
        offset += SC_ARGUMENT_BYTES;
        // remaining -= SC_ARGUMENT_BYTES;

        let pad_len = SC_ARGUMENT_BYTES - SC_ARGUMENT_ADDRESS_BYTES;
        assert!(arg0[..pad_len].iter().all(|&byte| byte == 0));
        recipient = Vec::from(&arg0[pad_len..]);

        let arg1 = &data_initial_chunk[offset..(offset + SC_ARGUMENT_BYTES)];

        if matches!(func_sig.as_deref(), Some(sig) if sig == &SC_FUNC_SIG_APPROVE)
            && arg1.iter().all(|&byte| byte == 255)
        {
            // "Unlimited" approval (all bits set) is a special case
            // which we encode as value=None internally.
            value = None;
            info!("Detected unlimited approval, treating value as None");
        } else {
            // TODO: better implement parsing int value from bytes
            assert!(arg1.len() <= 32);
            value = Some(U256::from_big_endian(arg1));
            // info!("Parsed value from function arguments: {}", value);
        }

        token = Some(definitions.get_token(address_bytes));
        token_address = Some(Vec::from(address_bytes));
    } else {
        // If the function was known but something else (data length) was unexpected,
        // pretend we did not recognize the function so we fall back to blind signing.
        // See the approve_avantis test case and ERC-8021.

        func_sig = None;
        info!(
            "Function signature not recognized or data length mismatch, treating as unknown function"
        );
    };

    Ok((token, token_address, func_sig, recipient, value))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::strutil::hex_decode;

    // Verify constants match the hex strings they replaced
    #[test]
    fn test_sc_func_sig_constants() {
        assert_eq!(
            SC_FUNC_SIG_TRANSFER,
            hex_decode("a9059cbb").unwrap().as_slice()
        );
        assert_eq!(
            SC_FUNC_SIG_APPROVE,
            hex_decode("095ea7b3").unwrap().as_slice()
        );
        assert_eq!(
            SC_FUNC_SIG_STAKE,
            hex_decode("3a29dbae").unwrap().as_slice()
        );
        assert_eq!(
            SC_FUNC_SIG_UNSTAKE,
            hex_decode("76ec871c").unwrap().as_slice()
        );
        assert_eq!(
            SC_FUNC_SIG_CLAIM,
            hex_decode("33986ffa").unwrap().as_slice()
        );
    }

    #[test]
    fn test_everstake_address_constants() {
        assert_eq!(
            &ADDRESSES_POOL[0][..],
            hex_decode("AFA848357154a6a624686b348303EF9a13F63264")
                .unwrap()
                .as_slice()
        );
        assert_eq!(
            &ADDRESSES_POOL[1][..],
            hex_decode("D523794C879D9eC028960a231F866758e405bE34")
                .unwrap()
                .as_slice()
        );
        assert_eq!(
            &ADDRESSES_ACCOUNTING[0][..],
            hex_decode("624087DD1904ab122A32878Ce9e933C7071F53B9")
                .unwrap()
                .as_slice()
        );
        assert_eq!(
            &ADDRESSES_ACCOUNTING[1][..],
            hex_decode("7a7f0b3c23C23a31cFcb0c44709be70d4D545c6e")
                .unwrap()
                .as_slice()
        );
    }

    #[test]
    fn test_approve_known_address_constants() {
        assert_eq!(
            &ADDR_UNISWAP_V3_ROUTER[..],
            hex_decode("e592427a0aece92de3edee1f18e0157c05861564")
                .unwrap()
                .as_slice()
        );
        assert_eq!(
            &ADDR_1INCH_V6[..],
            hex_decode("111111125421cA6dc452d289314280a0f8842A65")
                .unwrap()
                .as_slice()
        );
        assert_eq!(
            &ADDR_LIFI_DIAMOND[..],
            hex_decode("1231DEB6f5749EF6cE6943a275A1D3E7486F4EaE")
                .unwrap()
                .as_slice()
        );
    }
}

use crate::{
    alloc_types::{String, ToString, Vec, vec},
    common::get_encoded_address,
    helpers::{format_energy_amount, format_token_amount, format_trx_amount},
    proto::tron::{ResourceCode, TransferContract, TriggerSmartContract},
    strutil::hex_encode,
    uformat,
};
use primitive_types::U256;
use trezor_app_sdk::{
    Error, Result, ResultExt,
    modui::{
        self, ConfirmAction, ConfirmData, ConfirmProperties, ConfirmSummary, ConfirmValue,
        ExtraItem, Footer, Property, Severity, ShowNotice, ValueKind,
    },
};

pub(crate) fn confirm_message_hash(hash: &[u8]) -> Result<()> {
    let message_hash_hex = uformat!(
        "0x{}",
        hex_encode(hash)
            .map_err(|_| Error::DataError("Failed to hex-encode message hash"))
            .c()?
            .as_str()
    );

    modui::confirm_value(ConfirmValue::new(
        tr!("ethereum__title_confirm_message_hash"),
        &message_hash_hex,
        ValueKind::Text,
        None,
        None,
        None,
        "tron/message_hash",
        &[],
    ))
    .c()?
    .confirmed()
    .c()
}

fn get_account_info_items<'a>(
    account: Option<&'a str>,
    account_path: Option<&'a str>,
) -> Vec<Property<'a>> {
    let mut items = Vec::with_capacity(2);
    if let Some(acc) = account {
        items.push(Property::new(tr!("words__account"), acc, false))
    }
    if let Some(path) = account_path {
        items.push(Property::new(
            tr!("address_details__derivation_path"),
            path,
            false,
        ))
    }

    items
}

pub(crate) fn confirm_typed_data_final() -> Result<()> {
    modui::confirm_action(ConfirmAction::new(
        tr!("ethereum__title_confirm_typed_data"),
        tr!("ethereum__sign_eip712"),
        None,
        None,
        "tron/typed_data",
        &[],
        true,
    ))
    .c()?
    .confirmed()
    .c()
}

pub(crate) fn confirm_empty_typed_message() -> Result<()> {
    modui::confirm_value(ConfirmValue::new(
        tr!("ethereum__title_confirm_message"),
        "",
        ValueKind::Text,
        None,
        Some(tr!("ethereum__no_message_field")),
        None,
        "tron/message",
        &[],
    ))
    .c()?
    .confirmed()
    .c()
}

/// Shortens string to show the last <limit> characters.
pub(crate) fn limit_str(s: &str, limit: Option<usize>) -> String {
    let limit = limit.unwrap_or(16);
    if s.len() <= limit + 2 {
        return s.to_string();
    }

    uformat!("..{}", &s[s.len() - limit..])
}

/// Keep "0x" prefix in a separate chunk (#6601).
pub(crate) fn addr_pad(addr: &str, chunkify: bool) -> Result<String> {
    if !addr.starts_with("0x") {
        return Err(Error::DataError("Invalid address format"));
    }
    let mut addr = addr.to_string();
    if chunkify {
        addr = uformat!("  {}", addr.as_str());
    }
    Ok(addr)
}

/// A note attached to a transaction: free-form text supplied by the sender.
pub fn confirm_note(note: &str) -> Result<()> {
    modui::confirm_value(ConfirmValue::new(
        tr!("words__note"),
        note,
        ValueKind::Text,
        None,
        None,
        None,
        "tron/note",
        &[],
    ))
    .c()?
    .confirmed()
    .c()
}

pub fn confirm_freeze_operations(
    owner_address: &[u8],
    balance: u64,
    resource: i32,
    title: &str,
) -> Result<()> {
    let address = get_encoded_address(owner_address).c()?;
    modui::confirm_value(ConfirmValue::new(
        title,
        &address,
        ValueKind::Address,
        None,
        None,
        None,
        "tron/freeze/owner",
        &[],
    ))
    .c()?
    .confirmed()
    .c()?;

    let amount = format_trx_amount(balance);
    let resource = if resource == ResourceCode::Energy as i32 {
        "Energy"
    } else {
        "Bandwidth"
    };

    modui::confirm_properties(ConfirmProperties::new(
        tr!("words__title_summary"),
        &[
            Property::new(tr!("words__amount"), &amount, false),
            Property::new(tr!("words__resource"), resource, false),
        ],
        None,
        "tron/freeze",
        &[],
        false,
    ))
    .c()?
    .confirmed()
    .c()
}

pub fn confirm_claim(
    owner_address: Option<&str>,
    account_details: (Option<&str>, &str),
    intro_question: &str,
) -> Result<()> {
    let title = tr!("ethereum__staking_claim");

    // When the owner address differs from the signing address, confirm it first
    // (with a warning) so the final screen is the claim itself.
    if let Some(owner_address) = owner_address {
        modui::confirm_value(ConfirmValue::new(
            title,
            owner_address,
            ValueKind::Address,
            None,
            Some(tr!("tron__owner_address")),
            Some(Footer::Warning(tr!("address__warning_not_yours"))),
            "tron/claim/owner",
            &[],
        ))
        .c()?
        .confirmed()
        .c()?;
    }

    confirm_tron_claim(
        title,
        intro_question,
        account_details.0,
        Some(account_details.1),
    )
}

pub fn confirm_trx_transfer(
    contract: &TransferContract,
    account_details: (Option<&str>, &str),
) -> Result<()> {
    confirm_tron_send(
        Some(&format_trx_amount(contract.amount)),
        None,
        account_details,
        &get_encoded_address(&contract.to_address).c()?,
    )
}

pub fn confirm_tron_claim(
    title: &str,
    intro_question: &str,
    account: Option<&str>,
    account_path: Option<&str>,
) -> Result<()> {
    let account_properties = get_account_info_items(account, account_path);

    let extras = [ExtraItem::simple(
        tr!("address_details__account_info"),
        account_properties.as_slice(),
    )];
    let extras = if account_properties.is_empty() {
        &extras[..0]
    } else {
        &extras[..]
    };

    modui::confirm_action(ConfirmAction::new(
        title,
        intro_question,
        None,
        None,
        "tron/claim",
        extras,
        true,
    ))
    .c()?
    .confirmed()
    .c()
}

fn confirm_tron_summary(
    title: Option<&str>,
    amount: Option<&str>,
    fee: Option<&str>,
    account_details: Option<(Option<&str>, &str)>,
) -> Result<()> {
    let account_items = account_details.map(|(account, path)| {
        vec![
            Property::new(tr!("words__account"), account.unwrap_or(""), false),
            Property::new(tr!("address_details__derivation_path"), path, false),
        ]
    });
    let account_extra = account_items
        .as_deref()
        .map(|items| ExtraItem::simple(tr!("address_details__account_info"), items));
    let extras = account_extra.as_slice();

    modui::confirm_summary(ConfirmSummary::new(
        title.unwrap_or(tr!("words__send")),
        amount.map(|a| (tr!("words__amount"), a)),
        fee.map(|f| (tr!("words__fee_limit"), f)),
        "tron/summary",
        extras,
    ))
    .c()?
    .confirmed()
    .c()
}

fn confirm_tron_send(
    amount: Option<&str>,
    fee: Option<&str>,
    account_details: (Option<&str>, &str),
    address: &str,
) -> Result<()> {
    let account_items = [
        Property::plain(tr!("words__account"), account_details.0.unwrap_or("")),
        Property::plain(tr!("address_details__derivation_path"), account_details.1),
    ];
    let extras = [ExtraItem::simple(
        tr!("address_details__account_info"),
        &account_items,
    )];

    modui::confirm_value(ConfirmValue::new(
        tr!("words__send"),
        address,
        ValueKind::Address,
        Some(tr!("words__recipient")),
        None,
        Some(Footer::Hint(tr!("address__check_with_source"))),
        "tron/send",
        &extras,
    ))
    .c()?
    .confirmed()
    .c()?;

    confirm_tron_summary(Some(tr!("words__send")), amount, fee, Some(account_details))
}

pub fn confirm_tron_transfer(
    recipient_addr: &str,
    amount_str: &str,
    maximum_fee: &str,
) -> Result<()> {
    let title = tr!("words__send");

    modui::confirm_value(ConfirmValue::new(
        title,
        recipient_addr,
        ValueKind::Address,
        Some(tr!("words__recipient")),
        None,
        None,
        "tron/transfer",
        &[],
    ))
    .c()?
    .confirmed()
    .c()?;

    modui::confirm_properties(ConfirmProperties::new(
        title,
        &[
            Property::new(tr!("words__amount"), amount_str, false),
            Property::new(tr!("words__chain"), "Tron", true),
        ],
        None,
        "tron/transfer/amount",
        &[],
        false,
    ))
    .c()?
    .confirmed()
    .c()?;

    modui::confirm_summary(ConfirmSummary::new(
        title,
        None,
        Some((tr!("words__fee_limit"), maximum_fee)),
        "tron/transfer/summary",
        &[],
    ))
    .c()?
    .confirmed()
    .c()
}

fn confirm_tron_approve(
    recipient_addr: &str,
    amount_str: &str,
    is_revoke: bool,
    maximum_fee: &str,
) -> Result<()> {
    let (title, action_subtitle, value_subtitle, summary_view) = if is_revoke {
        (
            tr!("ethereum__approve_intro_title_revoke"),
            tr!("ethereum__approve_intro_revoke"),
            tr!("ethereum__approve_revoke_from"),
            Property::new(tr!("words__token"), &amount_str[2..], true),
        )
    } else {
        (
            tr!("ethereum__approve_intro_title"),
            tr!("ethereum__approve_intro"),
            tr!("ethereum__approve_to"),
            Property::new(tr!("ethereum__approve_amount_allowance"), amount_str, false),
        )
    };

    modui::confirm_action(ConfirmAction::new(
        title,
        action_subtitle,
        None,
        None,
        "tron/approve",
        &[],
        true,
    ))
    .c()?
    .confirmed()
    .c()?;

    modui::confirm_value(ConfirmValue::new(
        title,
        recipient_addr,
        ValueKind::Address,
        Some(value_subtitle),
        None,
        None,
        "tron/approve/spender",
        &[],
    ))
    .c()?
    .confirmed()
    .c()?;

    modui::confirm_properties(ConfirmProperties::new(
        title,
        &[
            summary_view,
            Property::new(tr!("words__chain"), "Tron", true),
        ],
        None,
        "tron/approve/amount",
        &[],
        false,
    ))
    .c()?
    .confirmed()
    .c()?;

    modui::confirm_summary(ConfirmSummary::new(
        title,
        None,
        Some((tr!("words__fee_limit"), maximum_fee)),
        "tron/approve/summary",
        &[],
    ))
    .c()?
    .confirmed()
    .c()
}

pub fn confirm_tron_voting<'a>(items: &[Property<'a>]) -> Result<()> {
    modui::confirm_properties(ConfirmProperties::new(
        tr!("words__review"),
        items,
        Some(tr!("words__voting")),
        "tron/vote",
        &[],
        false,
    ))
    .c()?
    .confirmed()
    .c()
}

fn confirm_ethereum_unknown_contract_warning() -> Result<()> {
    let content = uformat!(
        "{} {}",
        tr!("ethereum__unknown_contract_address"),
        tr!("words__know_what_your_doing")
    );

    modui::show_notice(ShowNotice::new(
        Severity::Danger,
        tr!("words__important"),
        &content,
        "tron/unknown_contract",
        &[],
        false,
    ))
    .c()?
    .confirmed()
    .c()
}

pub fn confirm_unknown_smart_contract(
    contract: &TriggerSmartContract,
    fee_limit: u64,
) -> Result<()> {
    confirm_ethereum_unknown_contract_warning().c()?;

    let contract_address = get_encoded_address(&contract.contract_address).c()?;
    modui::confirm_value(ConfirmValue::new(
        tr!("ethereum__token_contract"),
        &contract_address,
        ValueKind::Address,
        None,
        None,
        None,
        "tron/contract",
        &[],
    ))
    .c()?
    .confirmed()
    .c()?;

    // The app hands over the raw calldata and gets one outcome; hex rendering,
    // paging and the button labels belong to the library.
    modui::confirm_data(ConfirmData::new(
        tr!("ethereum__title_input_data"),
        &contract.data,
        None,
        "tron/contract/data",
        &[],
        true,
    ))
    .c()?
    .confirmed()
    .c()?;

    confirm_tron_summary(
        Some(tr!("words__title_summary")),
        None,
        Some(format_energy_amount(fee_limit).as_str()),
        None,
    )
}

pub fn confirm_known_trc20_smart_contract(
    is_approve: bool,
    recipient_addr: &[u8],
    amount_arg: &[u8],
    fee_limit: u64,
    token_decimals: u32,
    token_symbol: &str,
) -> Result<()> {
    if is_approve {
        let mut is_revoke = false;
        let amount_str = if amount_arg.iter().all(|&byte| byte == 255) {
            uformat!("{} {}", tr!("words__unlimited"), token_symbol)
        } else {
            if amount_arg.iter().all(|&byte| byte == 0) {
                is_revoke = true;
            }
            format_token_amount(
                U256::from_big_endian(amount_arg),
                token_decimals,
                token_symbol,
            )
        };

        confirm_tron_approve(
            &get_encoded_address(recipient_addr).c()?,
            &amount_str,
            is_revoke,
            &format_energy_amount(fee_limit),
        )
        .c()?;
    } else {
        confirm_tron_transfer(
            &get_encoded_address(recipient_addr).c()?,
            &format_token_amount(
                U256::from_big_endian(amount_arg),
                token_decimals,
                token_symbol,
            ),
            &format_energy_amount(fee_limit),
        )
        .c()?;
    }

    Ok(())
}

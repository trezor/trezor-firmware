use crate::{
    alloc_types::{String, ToString, Vec, vec},
    common::get_encoded_address,
    helpers::{format_energy_amount, format_token_amount, format_trx_amount},
    proto::{
        common::button_request::ButtonRequestType,
        tron::{ResourceCode, TransferContract, TriggerSmartContract},
    },
    sc_constants::SC_ARGUMENT_BYTES,
    strutil::hex_encode,
    uformat,
};
use primitive_types::U256;
use trezor_app_sdk::{
    Error, Result, ResultExt,
    ui::{self, ConfirmValue, Property, StrExt},
};

fn confirm_address(
    title: &str,
    address: &str,
    subtitle: Option<&str>,
    description: Option<&str>,
    verb: Option<&str>,
    footer: Option<(&str, bool)>,
    chunkify: Option<bool>,
    br_name: Option<&str>,
    br_code: i32,
) -> Result<()> {
    confirm_value(
        title,
        address,
        description,
        Some(br_name.unwrap_or("confirm_address")),
        br_code,
        true,
        verb,
        subtitle,
        false,
        chunkify.unwrap_or(true),
        None,
        None,
        footer,
    )?;
    Ok(())
}

pub(crate) fn confirm_message_hash(hash: &[u8]) -> Result<()> {
    let message_hash_hex = uformat!(
        "0x{}",
        hex_encode(hash)
            .map_err(|_| Error::DataError("Failed to hex-encode message hash"))?
            .as_str()
    );

    confirm_value(
        tr!("ethereum__title_confirm_message_hash"),
        &message_hash_hex,
        None,
        Some("confirm_message_hash"),
        ButtonRequestType::SignTx.into(),
        true,
        Some(tr!("buttons__confirm")),
        None,
        false,
        false,
        None,
        None,
        None,
    )?;
    Ok(())
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
    match ui::confirm_action(ui::ConfirmAction::new(
        tr!("ethereum__title_confirm_typed_data"),
        tr!("ethereum__sign_eip712"),
        None,
        None,
        true,
        Some(tr!("buttons__hold_to_confirm")),
        true,
        Some("confirm_typed_data_final"),
        ButtonRequestType::Other.into(),
        false,
    ))? {
        ui::TrezorUiResult::Confirmed => Ok(()),
        _ => Err(Error::Cancelled)?,
    }
}

pub(crate) fn confirm_empty_typed_message() -> Result<()> {
    confirm_text(
        "confirm_empty_typed_message",
        tr!("ethereum__title_confirm_message"),
        "",
        Some(tr!("ethereum__no_message_field")),
        ButtonRequestType::Other.into(),
    )
}

fn confirm_text(
    br_name: &str,
    title: &str,
    data: &str,
    description: Option<&str>,
    br_code: i32,
) -> Result<()> {
    confirm_value(
        title,
        data,
        description,
        Some(br_name),
        br_code,
        true,
        None,
        None,
        false,
        false,
        None,
        None,
        None,
    )?;
    Ok(())
}

/// Shortens string to show the last <limit> characters.
pub(crate) fn limit_str(s: &str, limit: Option<usize>) -> String {
    let limit = limit.unwrap_or(16);
    if s.len() <= limit + 2 {
        return s.to_string();
    }

    uformat!("..{}", &s[s.len() - limit..])
}

// TODO: implement remove
// pub(crate) fn require_confirm_other_data(data: &[u8], data_total: u32) -> Result<()> {
//     let description = uformat!("Size: {} bytes", data_total);
//     let subtitle = uformat!("All input data ({} bytes)", data_total);
//     let data_str = hex_encode(data);
//     ui::error_if_not_confirmed(ui::confirm_blob(
//         "Input data",
//         &data_str,
//         Some(&description),
//         Some(&subtitle),
//         "confirm_data",
//         ButtonRequestType::ButtonRequestSignTx.into(),
//         false,
//         Some("Confirm"),
//         Some("Cancel sign"),
//         false,
//         true,
//         true,
//     )?)?;
//     Ok(())
// }

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

/// General confirmation dialog, used by many other confirm_* functions.
pub fn confirm_value(
    title: &str,
    content: &str,
    description: Option<&str>,
    br_name: Option<&str>,
    br_code: i32,
    is_data: bool,
    verb: Option<&str>,
    subtitle: Option<&str>,
    hold: bool,
    chunkify: bool,
    info_items: Option<&[Property]>,
    info_title: Option<&str>,
    footer: Option<(&str, bool)>,
) -> Result<()> {
    let info_title = info_title.unwrap_or(tr!("words__title_information"));
    let details =
        info_items.map(|props| [ui::Details::new(info_title, props, None, None, br_code)]);
    let children: &[ui::Details] = details.as_ref().map(|d| d.as_slice()).unwrap_or(&[]);
    let menu = ui::Menu::new(children, Some(ui::Cancel::new(tr!("buttons__cancel"))));

    ui::error_if_not_confirmed(ui::interact_with_menu_flow(
        |name| {
            ui::confirm_value(ConfirmValue::new(
                title,
                content,
                description,
                name,
                br_code,
                is_data,
                verb,
                subtitle,
                false,
                hold,
                chunkify,
                false,
                false,
                true,
                footer,
            ))
        },
        &menu,
        br_name,
    )?)?;
    Ok(())
}

pub(crate) fn confirm_blob_intro(
    title: &str,
    value: &[u8],
    subtitle: &str,
    verb: &str,
    verb_cancel: &str,
    br_name: &str,
    br_code: ButtonRequestType,
) -> Result<bool> {
    // Introduce blob to be confirmed, allowing the user to:
    // - view (returns `False`)
    // - confirm (returns `True`)
    // - cancel (raises `ActionCancelled`)

    let value_str =
        hex_encode(value).map_err(|_| Error::DataError("Failed to hex-encode value"))?;

    let res = ui::confirm_value_intro(ui::ConfirmValueIntro::new(
        title,
        &value_str,
        Some(subtitle),
        Some(verb),
        Some(verb_cancel),
        false,
        false,
        Some(br_name),
        br_code.into(),
    ))?;

    match res {
        ui::TrezorUiResult::Confirmed => Ok(true),
        ui::TrezorUiResult::Info => Ok(false),
        _ => Err(Error::Cancelled)?,
    }
}

pub(crate) fn confirm_blob_prefix(
    data: &[u8],
    total_len: usize,
    confirmed_len: usize,
    br_name: &str,
    br_code: ButtonRequestType,
) -> Result<Option<usize>> {
    // Returns the number of bytes confirmed, or `None` if confirmation should be skipped.
    let prefix_len = core::cmp::min(9 * 9, data.len()); // 9 rows x 18 hex digits (2 chars per byte)
    let prefix = hex_encode(&data[..prefix_len])
        .map_err(|_| Error::DataError("Failed to hex-encode prefix"))?;
    let confirmed_len = confirmed_len + prefix.len();
    let verb = if confirmed_len < total_len {
        tr!("words__show_next")
    } else {
        tr!("buttons__continue")
    };

    // TODO: use tr ethereum__title_input_data_bytes
    let title = uformat!("Data:\n{} / {} bytes", confirmed_len, total_len);

    let show_more = !ui::should_show_more(
        &title,
        &[StrExt::new(&prefix, true)],
        tr!("words__confirm_all"), // will return True
        Some(br_name),
        br_code.into(),
        verb, // will return False
    )?;
    if show_more {
        return Ok(Some(prefix.len()));
    }
    Ok(None)
}

pub fn confirm_blob(
    title: &str,
    data: &str,
    description: Option<&str>,
    subtitle: Option<&str>,
    br_name: &str,
    br_code: i32,
    hold: bool,
    verb: Option<&str>,
    verb_cancel: Option<&str>,
    chunkify: bool,
    ask_pagination: bool,
    is_data: bool,
) -> Result<()> {
    if ask_pagination {
        ui::error_if_not_confirmed(ui::interact_with_info_flow(
            |name| {
                ui::confirm_value_intro(ui::ConfirmValueIntro::new(
                    title,
                    &data[..data.len().min(170)], /* TODO: be precise about the 1 st page */
                    description,
                    verb,
                    verb_cancel,
                    hold,
                    chunkify,
                    name,
                    br_code,
                ))
            },
            |name| {
                ui::confirm_value(ui::ConfirmValue::new(
                    subtitle.unwrap_or(title),
                    data,
                    None,
                    name,
                    br_code,
                    is_data,
                    None,
                    None,
                    false,
                    hold,
                    chunkify,
                    true,
                    true,
                    false,
                    None,
                ))
            },
            br_name,
            Some(true),
            Some(true),
        )?)?;
    } else {
        confirm_value(
            title,
            data,
            description,
            Some(br_name),
            br_code,
            true,
            verb,
            subtitle,
            hold,
            chunkify,
            None,
            None,
            None,
        )?;
    };
    Ok(())
}

pub fn confirm_freeze_operations(
    owner_address: &[u8],
    balance: u64,
    resource: i32,
    title: &str,
) -> Result<()> {
    confirm_address(
        title,
        &get_encoded_address(owner_address)?,
        None,
        None,
        None,
        None,
        Some(true),
        None,
        ButtonRequestType::Other.into(),
    )?;

    ui::confirm_properties(ui::ConfirmProperties::new(
        tr!("words__title_summary"),
        &[
            Property::new(tr!("words__amount"), &format_trx_amount(balance), false),
            Property::new(
                tr!("words__resource"),
                if resource == ResourceCode::Energy as i32 {
                    "Energy"
                } else {
                    "Bandwidth"
                },
                false,
            ),
        ],
        None,
        None,
        true,
        Some("tron/freeze"),
        ButtonRequestType::ConfirmOutput.into(),
    ))?;
    Ok(())
}

pub fn confirm_trx_transfer(
    contract: &TransferContract,
    account_details: (Option<&str>, &str),
) -> Result<()> {
    confirm_tron_send(
        Some(&format_trx_amount(contract.amount)),
        None,
        account_details,
        &get_encoded_address(&contract.to_address)?,
        true,
    )
}

pub fn confirm_tron_claim(
    title: &str,
    intro_question: &str,
    account: Option<&str>,
    account_path: Option<&str>,
    br_name: &str,
    br_code: i32,
) -> Result<()> {
    // let br_name: &str = "tron/claim";
    // let br_code: i32 = ButtonRequestType::SignTx.into();

    let mut menu_items = Vec::with_capacity(1);

    let account_properties = get_account_info_items(account, account_path);

    if !account_properties.is_empty() {
        menu_items.push(ui::Details::new(
            tr!("address_details__account_info"),
            account_properties.as_slice(),
            None,
            Some(tr!("send__send_from")),
            br_code,
        ));
    };

    ui::error_if_not_confirmed(ui::interact_with_menu_flow(
        |name| {
            ui::confirm_action(ui::ConfirmAction::new(
                title,
                intro_question,
                None,
                None,
                true,
                None,
                false,
                name,
                br_code,
                true,
            ))
        },
        &ui::Menu::new(&menu_items, None),
        Some(br_name),
    )?)?;

    Ok(())
}

fn confirm_tron_summary(
    title: Option<&str>,
    amount: Option<&str>,
    fee: Option<&str>,
    account_details: Option<(Option<&str>, &str)>,
) -> Result<()> {
    let account_items = if let Some(account_details) = account_details {
        Some(vec![
            Property::new(
                tr!("words__account"),
                account_details.0.unwrap_or(""),
                false,
            ),
            Property::new(
                tr!("address_details__derivation_path"),
                account_details.1,
                false,
            ),
        ])
    } else {
        None
    };

    let amount_label = if amount.is_some() {
        Some(tr!("words__amount"))
    } else {
        None
    };

    let fee_label = if fee.is_some() {
        tr!("words__fee_limit")
    } else {
        ""
    };

    ui::error_if_not_confirmed(ui::confirm_summary(ui::ConfirmSummary::new(
        title.unwrap_or(tr!("words__send")),
        amount,
        amount_label,
        fee.unwrap_or(""),
        fee_label,
        Some(tr!("address_details__account_info")),
        account_items.as_deref(),
        None,
        None,
        false,
        Some("tron/summary"),
        ButtonRequestType::SignTx.into(),
    ))?)?;

    Ok(())
}

fn confirm_tron_send(
    amount: Option<&str>,
    fee: Option<&str>,
    account_details: (Option<&str>, &str),
    address: &str,
    chunkify: bool,
) -> Result<()> {
    confirm_address(
        tr!("words__send"),
        address,
        Some(tr!("words__recipient")),
        None,
        Some(tr!("buttons__continue")),
        Some((tr!("address__check_with_source"), false)),
        Some(chunkify),
        Some("tron/send"),
        ButtonRequestType::Other.into(),
        // info_items = [
        //     (TR.words__account, account_details[0], False),
        //     (
        //         TR.address_details__derivation_path,
        //         account_details[1],
        //         False,
        //     ),
        // ],
        // info_title = TR.address_details__account_info,
    )?;
    confirm_tron_summary(Some(tr!("words__send")), amount, fee, Some(account_details))?;
    Ok(())
}

pub fn confirm_tron_transfer(
    recipient_addr: &str,
    amount_str: &str,
    maximum_fee: &str,
    chunkify: bool,
) -> Result<()> {
    let br_name = "tron/transfer";
    let title = tr!("words__send");

    ui::error_if_not_confirmed(ui::confirm_value(ui::ConfirmValue::new(
        title,
        recipient_addr,
        None,
        Some(br_name),
        ButtonRequestType::Other.into(),
        true,
        Some(tr!("buttons__continue")),
        Some(tr!("words__recipient")),
        false,
        false,
        chunkify,
        false,
        false,
        false,
        None,
    ))?)?;

    let properties = vec![
        Property::new(tr!("words__amount"), amount_str, false),
        Property::new(tr!("words__chain"), "Tron", true),
    ];

    ui::confirm_properties(ui::ConfirmProperties::new(
        title,
        &properties,
        None,
        Some(tr!("buttons__continue")),
        false,
        Some(br_name),
        ButtonRequestType::ConfirmOutput.into(),
    ))?;

    ui::error_if_not_confirmed(ui::confirm_summary(ui::ConfirmSummary::new(
        title,
        None,
        None,
        maximum_fee,
        tr!("words__fee_limit"),
        None,
        None,
        None,
        None,
        false,
        Some("confirm_total"),
        ButtonRequestType::SignTx.into(),
    ))?)?;

    Ok(())
}

fn confirm_tron_approve(
    recipient_addr: &str,
    amount_str: &str,
    is_revoke: bool,
    maximum_fee: &str,
    chunkify: bool,
) -> Result<()> {
    let br_name = "tron/approve";

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

    ui::confirm_action(ui::ConfirmAction::new(
        title,
        action_subtitle,
        None,
        None,
        false,
        Some(tr!("buttons__continue")),
        false,
        Some(br_name),
        ButtonRequestType::Other.into(),
        false,
    ))?;

    ui::confirm_value(ui::ConfirmValue::new(
        title,
        recipient_addr,
        None,
        Some(br_name),
        ButtonRequestType::Other.into(),
        true,
        Some(tr!("buttons__continue")),
        Some(value_subtitle),
        false,
        false,
        chunkify,
        false,
        false,
        false,
        None,
    ))?;

    let properties = [
        summary_view,
        Property::new(tr!("words__chain"), "Tron", true),
    ];

    ui::confirm_properties(ui::ConfirmProperties::new(
        title,
        &properties,
        None,
        Some(tr!("buttons__continue")),
        false,
        Some(br_name),
        ButtonRequestType::ConfirmOutput.into(),
    ))?;

    ui::confirm_summary(ui::ConfirmSummary::new(
        title,
        None,
        None,
        maximum_fee,
        tr!("words__fee_limit"),
        None,
        None,
        None,
        None,
        false,
        Some("confirm_total"),
        ButtonRequestType::SignTx.into(),
    ))?;

    Ok(())
}

fn confirm_tron_voting<'a>(items: &[Property<'a>]) -> Result<()> {
    // let mut item_list = Vec::new();
    // for (vote_count, address) in voting_list {
    //     item_list.push(Property::new(tr!("words__address"), address, true));
    //     item_list.push(Property::new(
    //         uformat!("\n{}", tr!("words__votes")),
    //         uformat!("{}", vote_count),
    //         false,
    //     ));
    // }

    ui::error_if_not_confirmed(ui::confirm_properties(ui::ConfirmProperties::new(
        tr!("words__review"),
        &items,
        Some(tr!("words__voting")),
        None,
        true,
        Some("tron/vote"),
        ButtonRequestType::SignTx.into(),
    ))?)?;

    Ok(())
}

fn confirm_ethereum_unknown_contract_warning(title: Option<&str>) -> Result<()> {
    let content = uformat!(
        "{} {}",
        tr!("ethereum__unknown_contract_address"),
        tr!("words__know_what_your_doing")
    );
    ui::show_danger(ui::ShowDanger::new(
        tr!("words__important"),
        &content,
        Some("unknown_contract_warning"),
        ButtonRequestType::Warning.into(),
        Some(tr!("send__cancel_sign")),
        title,
    ))?;

    Ok(())
}

pub fn confirm_unknown_smart_contract(
    contract: &TriggerSmartContract,
    fee_limit: u64,
) -> Result<()> {
    confirm_ethereum_unknown_contract_warning(Some(tr!("words__send")))?;

    let contract_address = get_encoded_address(&contract.contract_address)?;

    confirm_address(
        tr!("ethereum__token_contract"),
        &contract_address,
        None,
        None,
        None,
        None,
        Some(true),
        None,
        ButtonRequestType::Other.into(),
    )?;

    confirm_blob(
        tr!("ethereum__title_input_data"),
        &hex_encode(&contract.data)
            .map_err(|_| Error::DataError("Failed to hexlify contract data"))?,
        None,
        None,
        "confirm_smart_contract_data",
        ButtonRequestType::SignTx.into(),
        false,
        Some(tr!("buttons__confirm")),
        Some(tr!("send__cancel_sign")),
        false,
        true,
        false,
    )?;

    confirm_tron_summary(
        Some(tr!("words__title_summary")),
        None,
        Some(format_energy_amount(fee_limit).as_str()),
        None,
    )?;

    Ok(())
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
        if amount_arg.iter().all(|&byte| byte == 255) {
            let amount_str = uformat!("{} {}", tr!("words__unlimited"), token_symbol);
        } else {
            if amount_arg.iter().all(|&byte| byte == 0) {
                is_revoke = true;
            }
            let amount_str = format_token_amount(
                U256::from_big_endian(amount_arg),
                token_decimals,
                token_symbol,
            );

            confirm_tron_approve(
                &get_encoded_address(recipient_addr)?,
                &amount_str,
                is_revoke,
                &format_energy_amount(fee_limit),
                true,
            )?;
        }
    } else {
        confirm_tron_transfer(
            &get_encoded_address(recipient_addr)?,
            &format_token_amount(
                U256::from_big_endian(amount_arg),
                token_decimals,
                token_symbol,
            ),
            &format_energy_amount(fee_limit),
            true,
        )?;
    }

    Ok(())
}

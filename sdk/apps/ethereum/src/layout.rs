use crate::{
    clear_signing_definitions::SC_FUNC_APPROVE_REVOKE_AMOUNT,
    definitions,
    helpers::{
        Refund, Trade, address_from_bytes, decode_typed_data, format_ethereum_amount,
        get_type_name, is_swap,
    },
    paths::Bip32Path,
    payment_request::parse_amount,
    proto::{
        common::{PaymentRequest, button_request::ButtonRequestType},
        definitions::{NetworkInfo, TokenInfo},
        ethereum::typed_data_struct_ack::{DataType, FieldType, StructMember},
    },
    sc_constants::get_approve_known_address,
    strutil::{format_plural_english, hex_encode},
    tokens, uformat,
    yielding::{FUNC_SIG_DEPOSIT, FUNC_SIG_REDEEM, FUNC_SIG_WITHDRAW},
};
#[cfg(not(test))]
use alloc::{
    string::{String, ToString},
    vec,
    vec::Vec,
};
use primitive_types::U256;
#[cfg(test)]
use std::{
    string::{String, ToString},
    vec,
    vec::Vec,
};
use trezor_app_sdk::{
    Error, Result,
    ui::{self, Property, StrExt},
    unwrap,
};

// TODO: This threshold is arbitrary
const LONG_MSG_PAGE_THRESHOLD: usize = 300;

pub(crate) fn require_confirm_approve<'a>(
    recipient_addr: &'a str,
    total_amount: Option<&'a str>,
    recipient_str: Option<&'a str>,
    dp: &'a Bip32Path,
    maximum_fee: &'a str,
    fee_info_items: &[Property<'a>],
    chain_id: u64,
    network: &'a NetworkInfo,
    token: &'a TokenInfo,
    token_address: &'a [u8],
    is_revoke: bool,
    chunkify: bool,
) -> Result<()> {
    let chain_id_str = uformat!("{} (0x{:x})", chain_id, chain_id);
    let token_address_str = address_from_bytes(token_address, Some(network));
    let (_, account_path) = dp.account_and_path();

    let is_unknown_token = token == &tokens::unknown_token();
    let is_unknown_network = network == &definitions::unknown_network();

    if is_unknown_token {
        let title = if is_revoke {
            tr!("ethereum__approve_intro_title_revoke")
        } else {
            tr!("ethereum__approve_intro_title")
        };
        require_confirm_unknown_token(title)?;
    }

    confirm_ethereum_approve(
        &addr_pad(&recipient_addr, chunkify),
        recipient_str,
        is_unknown_token,
        &addr_pad(&token_address_str, chunkify),
        &token.symbol,
        is_unknown_network,
        &chain_id_str,
        &network.name,
        is_revoke,
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
    let (title, action) = if is_revoke {
        (
            tr!("ethereum__approve_intro_title_revoke"),
            tr!("ethereum__approve_intro_revoke"),
        )
    } else {
        (
            tr!("ethereum__approve_intro_title"),
            tr!("ethereum__approve_intro"),
        )
    };

    ui::error_if_not_confirmed(ui::confirm_action(
        title,
        action,
        None,
        None,
        false,
        Some(tr!("buttons__continue")),
        false,
        Some(br_name),
        ButtonRequestType::ButtonRequestOther.into(),
        false,
    )?)?;

    let subtitle = if is_revoke {
        tr!("ethereum__approve_revoke_from")
    } else {
        tr!("ethereum__approve_to")
    };

    if let Some(recipient_str) = recipient_str {
        ui::interact_with_info_flow(
            |name| {
                ui::confirm_with_info(
                    title,
                    Some(subtitle),
                    &[StrExt::new(recipient_str, true)],
                    tr!("buttons__continue"),
                    Some(tr!("ethereum__contract_address")),
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
        ui::error_if_not_confirmed(ui::confirm_value(
            title,
            recipient_addr,
            None,
            Some(br_name),
            br_code,
            true,
            Some(tr!("buttons__continue")),
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
            tr!("words__important"),
            &content,
            tr!("words__continue_anyway"),
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
            Some(tr!("ethereum__title_token_contract")),
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
            Some(tr!("ethereum__approve_chain_id")),
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
        props.push(Property::new(tr!("words__token"), token_symbol, true));
    } else {
        props.push(Property::new(
            tr!("ethereum__approve_amount_allowance"),
            total_amount.unwrap_or(tr!("words__unlimited")),
            false,
        ));
    }
    if !is_unknown_network {
        props.push(Property::new(tr!("words__chain"), network_name, false));
    }

    ui::error_if_not_confirmed(ui::confirm_properties(
        title,
        &props,
        None,
        Some(tr!("buttons__continue")),
        false,
        Some(br_name),
        ButtonRequestType::ButtonRequestOther.into(),
    )?)?;

    let account_item = account_path.map(|p| {
        [Property::new(
            tr!("address_details__derivation_path"),
            p,
            true,
        )]
    });

    ui::error_if_not_confirmed(ui::confirm_summary(
        Some(title),
        None,
        None,
        maximum_fee,
        tr!("send__maximum_fee"),
        None,
        account_item.as_ref().map(|a| a.as_slice()),
        Some(tr!("confirm_total__title_fee")),
        Some(fee_info_items),
        false,
        Some("confirm_total"),
        ButtonRequestType::ButtonRequestOther.into(),
    )?)?;

    Ok(())
}

pub(crate) fn require_confirm_clear_signing(
    recipient_str: &str,
    intent: &str,
    properties: &[Property],
    maximum_fee: &str,
) -> Result<()> {
    confirm_ethereum_clear_signing(recipient_str, intent, properties, maximum_fee)?;
    Ok(())
}

fn confirm_ethereum_clear_signing(
    recipient_str: &str,
    intent: &str,
    properties: &[Property],
    maximum_fee: &str,
) -> Result<()> {
    ui::confirm_action(
        tr!("words__provider"),
        recipient_str,
        None,
        None,
        false,
        None,
        false,
        Some("confirm_contract"),
        ButtonRequestType::ButtonRequestOther.into(),
        false,
    )?;
    ui::confirm_action(
        tr!("words__intent"),
        intent,
        None,
        None,
        false,
        None,
        false,
        Some("confirm_contract"),
        ButtonRequestType::ButtonRequestOther.into(),
        false,
    )?;
    ui::confirm_properties(
        tr!("ethereum__confirm_contract"),
        properties,
        None,
        None,
        false,
        Some("confirm_contract"),
        ButtonRequestType::ButtonRequestOther.into(),
    )?;
    ui::error_if_not_confirmed(ui::confirm_summary(
        None,
        None,
        None,
        maximum_fee,
        tr!("send__maximum_fee"),
        None,
        None,
        None,
        None,
        false,
        Some("confirm_ethereum_tx"),
        ButtonRequestType::ButtonRequestOther.into(),
    )?)?;

    Ok(())
}

pub(crate) fn require_confirm_tx<'a>(
    recipient: Option<&'a str>,
    total_amount: &'a str,
    address_bytes: &'a [u8],
    dp: &'a Bip32Path,
    maximum_fee: &'a str,
    fee_info_items: &'a [Property<'a>],
    token: Option<&'a TokenInfo>,
    is_send: bool,
    chunkify: bool,
) -> Result<()> {
    let (account, account_path) = dp.account_and_path();

    if let Some(token) = token {
        if token == &tokens::unknown_token() {
            let title = tr!("words__send");
            require_confirm_unknown_token(title)?;
            require_confirm_address(
                address_bytes,
                Some(title),
                Some(tr!("ethereum__title_token_contract")),
                Some(tr!("buttons__continue")),
                Some("unknown_token"),
                Some(tr!("ethereum__unknown_contract_address")),
            )?;
        }
    }

    let recipient = recipient.map(|r| addr_pad(r, chunkify));

    confirm_ethereum_tx(
        recipient.as_deref(),
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
        Some(tr!("words__recipient"))
    } else {
        Some(tr!("ethereum__interaction_contract"))
    };
    let title = tr!("words__send");

    let account_properties = get_account_info_items(account, account_path);
    let menu_items = &[ui::Details::new(
        tr!("address_details__account_info"),
        &account_properties,
        None,
        Some(tr!("send__send_from")),
        ButtonRequestType::ButtonRequestOther.into(),
    )];

    let menu = ui::Menu::new(menu_items, Some(ui::Cancel::new(tr!("send__cancel_sign"))));

    let steps: [&dyn Fn() -> ui::UiResult; 2] = [
        &|| {
            ui::interact_with_menu_flow(
                |name| {
                    ui::confirm_value(
                        title,
                        recipient.unwrap_or(tr!("ethereum__new_contract")),
                        None,
                        name,
                        br_code,
                        recipient.is_some(),
                        Some(tr!("buttons__continue")),
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
                Some(tr!("words__amount")),
                maximum_fee,
                tr!("send__maximum_fee"),
                None,
                None,
                Some(tr!("confirm_total__title_fee")),
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

pub(crate) fn require_confirm_payment_request<'a>(
    provider_address: &'a str,
    verified_payment_req: &'a PaymentRequest,
    dp: &'a Bip32Path,
    maximum_fee: &'a str,
    fee_info_items: &'a [Property<'a>],
    chain_id: u64,
    network: &'a NetworkInfo,
    token: Option<&'a TokenInfo>,
    token_address: Option<&'a str>,
) -> Result<()> {
    let total_amount = format_ethereum_amount(
        parse_amount(unwrap!(verified_payment_req.amount.as_deref()))?,
        token,
        network,
        false,
    );

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
            return Err(Error::DataError(
                "Unrecognized memo type in payment request.",
            ));
        }
    }

    let (account, account_path) = dp.account_and_path();
    let mut account_items = Vec::with_capacity(3);
    if let Some(ref account) = account {
        account_items.push(Property::new(tr!("words__account"), account.as_str(), true));
    }
    if let Some(ref account_path) = account_path {
        account_items.push(Property::new(
            tr!("address_details__derivation_path"),
            account_path.as_str(),
            true,
        ));
    }
    let chain_id_str = uformat!("{} ({})", network.name.as_str(), chain_id);
    if chain_id != 0 {
        account_items.push(Property::new(
            tr!("ethereum__approve_chain_id"),
            chain_id_str.as_str(),
            true,
        ));
    }

    let extra_menu_items = if let Some(token_address) = token_address {
        Some([(tr!("ethereum__title_token_contract"), token_address)])
    } else {
        None
    };

    confirm_payment_request(
        verified_payment_req.recipient_name.as_str(),
        Some(&provider_address),
        texts.as_slice(),
        &refunds,
        &trades,
        &account_items,
        Some(maximum_fee),
        Some(fee_info_items),
        extra_menu_items.as_ref().map(|e| e.as_slice()),
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
        (tr!("words__swap"), tr!("words__swap"))
    } else {
        (tr!("buttons__confirm"), tr!("words__title_summary"))
    };

    for (text_title, text) in texts {
        ui::error_if_not_confirmed(ui::confirm_value(
            text_title.unwrap_or(title),
            text,
            None,
            Some("confirm_payment_request"),
            ButtonRequestType::ButtonRequestOther.into(),
            true,
            Some(tr!("buttons__confirm")),
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

    let mut menu_items = Vec::with_capacity(3);

    let props;
    if let Some(recipient_address) = recipient_address {
        props = [Property::new("", recipient_address, true)];
        menu_items.push(ui::Details::new(
            tr!("address__title_provider_address"),
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
            refund_account_info.push(Property::new(
                tr!("words__account"),
                refund_account.as_str(),
                true,
            ));
        }

        if let Some(ref refund_account_path) = refund.account_path {
            refund_account_info.push(Property::new(
                tr!("address_details__derivation_path"),
                refund_account_path.as_str(),
                true,
            ));
        }

        refund_account_infos.push(refund_account_info);
    }

    for refund_account_info in &refund_account_infos {
        menu_items.push(ui::Details::new(
            tr!("address__title_refund_address"),
            refund_account_info.as_slice(),
            None,
            None,
            ButtonRequestType::ButtonRequestOther.into(),
        ));
    }

    let menu = ui::Menu::new(
        menu_items.as_slice(),
        Some(ui::Cancel::new(tr!("send__cancel_sign"))),
    );

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
                    Some(tr!("buttons__continue")),
                    Some(tr!("words__provider")),
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
                        tr!("words__assets"),
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
                        tr!("words__transaction_fee"),
                        None,
                        Some(account_items),
                        Some(tr!("confirm_total__title_fee")),
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

pub(crate) fn require_confirm_stake<'a>(
    address_bytes: &[u8],
    value: U256,
    dp: &'a Bip32Path,
    maximum_fee: &'a str,
    fee_info_items: &'a [Property<'a>],
    network: &'a NetworkInfo,
    chunkify: bool,
) -> Result<()> {
    let address_str = addr_pad(&address_from_bytes(address_bytes, Some(network)), chunkify);
    let total_amount = format_ethereum_amount(value, None, network, false);
    let (account, account_path) = dp.account_and_path();

    confirm_ethereum_staking_tx(
        tr!("ethereum__staking_stake"),
        tr!("ethereum__staking_stake_intro"),
        tr!("ethereum__staking_stake"),
        &total_amount,
        account.as_deref(),
        account_path.as_deref(),
        maximum_fee,
        &address_str,
        tr!("ethereum__staking_stake_address"),
        fee_info_items,
        None,
        None,
    )?;

    Ok(())
}

pub(crate) fn require_confirm_vault_tx<'a>(
    value: U256,
    dp: &'a Bip32Path,
    maximum_fee: &'a str,
    fee_info_items: &'a [Property<'a>],
    network: &'a NetworkInfo,
    vault_str: &'a str,
    token: TokenInfo,
    func_sig: &'a [u8],
    extra_data: Option<&'a [u8]>,
) -> Result<()> {
    let (title, intro_question, verb, amount_label, br_name) = if func_sig == FUNC_SIG_DEPOSIT {
        (
            tr!("words__deposit"),
            tr!("ethereum__vault_deposit_intro"),
            tr!("ethereum__deposit_to"),
            tr!("ethereum__deposit_amount"),
            "ethereum/vault/deposit",
        )
    } else if func_sig == FUNC_SIG_REDEEM {
        (
            tr!("ethereum__redeem"),
            tr!("ethereum__vault_redeem_intro"),
            tr!("ethereum__redeem_from"),
            tr!("ethereum__redeem_amount"),
            "ethereum/vault/redeem",
        )
    } else if func_sig == FUNC_SIG_WITHDRAW {
        (
            tr!("ethereum__withdraw"),
            tr!("ethereum__vault_withdraw_intro"),
            tr!("ethereum__withdraw_from"),
            tr!("ethereum__withdraw_amount"),
            "ethereum/vault/withdraw",
        )
    } else {
        return Err(Error::ValueError("Unknown vault function signature"));
    };

    let amount = format_ethereum_amount(value, Some(&token), network, false);
    let (account, account_path) = dp.account_and_path();

    let extra_data_str = extra_data.map(|b| uformat!("0x{}", hex_encode(b).as_str()));

    confirm_ethereum_vault_tx(
        title,
        intro_question,
        verb,
        vault_str,
        &amount,
        amount_label,
        account.as_deref(),
        account_path.as_deref(),
        maximum_fee,
        fee_info_items,
        &network.name,
        Some(br_name),
        None,
        extra_data_str.as_deref(),
    )?;
    Ok(())
}

fn confirm_ethereum_vault_tx(
    title: &str,
    intro_question: &str,
    verb: &str,
    vault_str: &str,
    amount: &str,
    amount_label: &str,
    account: Option<&str>,
    account_path: Option<&str>,
    maximum_fee: &str,
    info_items: &[Property],
    chain: &str,
    br_name: Option<&str>,
    br_code: Option<i32>,
    extra_data: Option<&str>,
) -> Result<()> {
    let br_name = br_name.unwrap_or("ethereum/vault");
    let br_code = br_code.unwrap_or(ButtonRequestType::ButtonRequestSignTx.into());

    let mut menu_items = Vec::with_capacity(1);
    let account_properties = get_account_info_items(account, account_path);
    if !account_properties.is_empty() {
        menu_items.push(ui::Details::new(
            tr!("address_details__account_info"),
            account_properties.as_slice(),
            None,
            Some(tr!("send__send_from")),
            ButtonRequestType::ButtonRequestOther.into(),
        ))
    }

    let menu = ui::Menu::new(&menu_items, Some(ui::Cancel::new(tr!("send__cancel_sign"))));

    let step1 = || {
        ui::interact_with_menu_flow(
            |name| {
                ui::confirm_action(
                    title,
                    intro_question,
                    None,
                    None,
                    false,
                    None,
                    false,
                    name,
                    br_code,
                    true,
                )
            },
            &menu,
            Some(&uformat!("{}/intro", br_name)),
        )
    };

    let step2 = || {
        ui::interact_with_menu_flow(
            |name| {
                ui::confirm_with_info(
                    title,
                    Some(verb),
                    &[StrExt::new(vault_str, true)],
                    tr!("buttons__continue"),
                    None,
                    name,
                    br_code,
                )
            },
            &menu,
            Some(&uformat!("{}/vault_name", br_name)),
        )
    };

    let step3 = || {
        ui::interact_with_menu_flow(
            |name| {
                ui::confirm_properties(
                    title,
                    &[
                        ui::Property::new(amount_label, amount, false),
                        ui::Property::new(tr!("words__chain"), chain, false),
                    ],
                    None,
                    Some(tr!("buttons__continue")),
                    false,
                    name,
                    br_code,
                )
            },
            &menu,
            Some(&uformat!("{}/amount", br_name)),
        )
    };

    let step4 = || {
        ui::interact_with_menu_flow(
            |name| {
                ui::confirm_properties(
                    title,
                    &[ui::Property::new(
                        tr!("ethereum__calldata_suffix"),
                        extra_data.unwrap_or_default(),
                        true,
                    )],
                    None,
                    Some(tr!("buttons__continue")),
                    false,
                    name,
                    br_code,
                )
            },
            &menu,
            Some(&uformat!("{}/extra_data", br_name)),
        )
    };

    let mut steps: Vec<&dyn Fn() -> ui::UiResult> = vec![&step1, &step2, &step3];

    if extra_data.is_some() {
        steps.push(&step4);
    }

    let step5 = || {
        ui::interact_with_menu_flow(
            |name| {
                ui::confirm_summary(
                    Some(title),
                    None,
                    None,
                    maximum_fee,
                    tr!("send__maximum_fee"),
                    None,
                    None,
                    Some(tr!("confirm_total__title_fee")),
                    Some(info_items),
                    false,
                    name,
                    br_code,
                )
            },
            &menu,
            Some(&uformat!("{}/summary", br_name)),
        )
    };

    steps.push(&step5);

    ui::error_if_not_confirmed(ui::confirm_linear_flow(&steps)?)?;
    Ok(())
}

pub(crate) fn require_confirm_claim_rewards(
    dp: &Bip32Path,
    maximum_fee: &str,
    fee_info_items: &[Property],
    token_labels: &[&str],
) -> Result<()> {
    let (account, account_path) = dp.account_and_path();
    let token_list = token_labels.join("\n");
    confirm_ethereum_vault_claim(
        tr!("ethereum__rewards_claim"),
        tr!("ethereum__vault_claim_intro"),
        account.as_deref(),
        account_path.as_deref(),
        maximum_fee,
        fee_info_items,
        &token_list,
        "ethereum/vault/claim",
        None,
    )?;
    Ok(())
}

fn confirm_ethereum_vault_claim(
    title: &str,
    intro_question: &str,
    account: Option<&str>,
    account_path: Option<&str>,
    maximum_fee: &str,
    info_items: &[Property],
    token_list: &str,
    br_name: &str,
    br_code: Option<i32>,
) -> Result<()> {
    let br_code = br_code.unwrap_or(ButtonRequestType::ButtonRequestSignTx.into());
    let mut menu_items = Vec::with_capacity(1);
    let account_properties = get_account_info_items(account, account_path);
    if !account_properties.is_empty() {
        menu_items.push(ui::Details::new(
            tr!("address_details__account_info"),
            &account_properties,
            None,
            Some(tr!("send__send_from")),
            ButtonRequestType::ButtonRequestOther.into(),
        ))
    }

    let menu = ui::Menu::new(&menu_items, Some(ui::Cancel::new(tr!("send__cancel_sign"))));
    let steps: [&dyn Fn() -> ui::UiResult; 3] = [
        &|| {
            ui::interact_with_menu_flow(
                |name| {
                    ui::confirm_action(
                        title,
                        intro_question,
                        None,
                        None,
                        false,
                        None,
                        false,
                        name,
                        br_code,
                        true,
                    )
                },
                &menu,
                Some(&uformat!("{}/intro", br_name)),
            )
        },
        &|| {
            ui::interact_with_menu_flow(
                |name| {
                    ui::confirm_properties(
                        title,
                        &[ui::Property::new(
                            tr!("ethereum__reward_tokens"),
                            token_list,
                            false,
                        )],
                        None,
                        Some(tr!("buttons__continue")),
                        false,
                        name,
                        br_code,
                    )
                },
                &menu,
                Some(&uformat!("{}/tokens", br_name)),
            )
        },
        &|| {
            ui::interact_with_menu_flow(
                |name| {
                    ui::confirm_summary(
                        Some(title),
                        None,
                        None,
                        maximum_fee,
                        tr!("send__maximum_fee"),
                        None,
                        None,
                        Some(tr!("confirm_total__title_fee")),
                        Some(info_items),
                        false,
                        name,
                        br_code,
                    )
                },
                &menu,
                Some(&uformat!("{}/summary", br_name)),
            )
        },
    ];
    ui::error_if_not_confirmed(ui::confirm_linear_flow(&steps)?)?;
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
    assert!(
        verb == tr!("ethereum__staking_stake")
            || verb == tr!("ethereum__staking_unstake")
            || verb == tr!("ethereum__staking_claim")
    );

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
            tr!("address_details__account_info"),
            &account_properties,
            None,
            Some(tr!("send__send_from")),
            ButtonRequestType::ButtonRequestOther.into(),
        ));
    };

    let amount_label = if verb == tr!("ethereum__staking_claim") {
        None
    } else {
        Some(tr!("words__amount"))
    };

    let menu = ui::Menu::new(
        menu_items.as_slice(),
        Some(ui::Cancel::new(tr!("send__cancel_sign"))),
    );

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
                tr!("send__maximum_fee"),
                None,
                None,
                Some(tr!("confirm_total__title_fee")),
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

pub(crate) fn require_confirm_unstake<'a>(
    address_bytes: &'a [u8],
    value: U256,
    dp: &'a Bip32Path,
    maximum_fee: &'a str,
    fee_info_items: &'a [Property<'a>],
    network: &'a NetworkInfo,
    chunkify: bool,
) -> Result<()> {
    let address_str = addr_pad(&address_from_bytes(address_bytes, Some(network)), chunkify);
    let total_amount = format_ethereum_amount(value, None, network, false);
    let (account, account_path) = dp.account_and_path();

    confirm_ethereum_staking_tx(
        tr!("ethereum__staking_unstake"),
        tr!("ethereum__staking_unstake_intro"),
        tr!("ethereum__staking_unstake"),
        &total_amount,
        account.as_deref(),
        account_path.as_deref(),
        maximum_fee,
        &address_str,
        tr!("ethereum__staking_stake_address"),
        fee_info_items,
        None,
        None,
    )?;

    Ok(())
}

pub(crate) fn require_confirm_claim<'a>(
    address_bytes: &'a [u8],
    dp: &'a Bip32Path,
    maximum_fee: &'a str,
    fee_info_items: &'a [Property<'a>],
    network: &'a NetworkInfo,
    chunkify: bool,
) -> Result<()> {
    let addr_str = addr_pad(&address_from_bytes(address_bytes, Some(network)), chunkify);
    let (account, account_path) = dp.account_and_path();

    confirm_ethereum_staking_tx(
        tr!("ethereum__staking_claim"),
        tr!("ethereum__staking_claim_intro"),
        tr!("ethereum__staking_claim"),
        "",
        account.as_deref(),
        account_path.as_deref(),
        maximum_fee,
        &addr_str,
        tr!("ethereum__staking_claim_address"),
        fee_info_items,
        None,
        None,
    )?;

    Ok(())
}

fn require_confirm_unknown_token(title: &str) -> Result<()> {
    confirm_ethereum_unknown_contract_warning(Some(title))?;
    Ok(())
}

fn confirm_ethereum_unknown_contract_warning(title: Option<&str>) -> Result<()> {
    let content = uformat!(
        "{} {}",
        tr!("ethereum__unknown_contract_address"),
        tr!("words__know_what_your_doing")
    );
    ui::show_danger(
        tr!("words__important"),
        &content,
        Some("unknown_contract_warning"),
        ButtonRequestType::ButtonRequestWarning.into(),
        Some(tr!("send__cancel_sign")),
        title,
    )?;

    Ok(())
}

pub(crate) fn require_confirm_address(
    address_bytes: &[u8],
    title: Option<&'static str>,
    subtitle: Option<&'static str>,
    verb: Option<&'static str>,
    br_name: Option<&'static str>,
    footer: Option<&'static str>,
) -> Result<()> {
    let address_hex = uformat!("0x{}", hex_encode(address_bytes).as_str());
    return confirm_address(
        title.unwrap_or(tr!("ethereum__title_signing_address")),
        &address_hex,
        subtitle,
        None,
        verb,
        footer.map(|f| (f, true)),
        None,
        br_name,
        ButtonRequestType::ButtonRequestSignTx.into(),
    );
}

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
    let message_hash_hex = uformat!("0x{}", hex_encode(hash).as_str());

    confirm_value(
        tr!("ethereum__title_confirm_message_hash"),
        &message_hash_hex,
        None,
        Some("confirm_message_hash"),
        ButtonRequestType::ButtonRequestSignTx.into(),
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
    account.map(|acc| items.push(Property::new(tr!("words__account"), acc, false)));
    account_path.map(|path| {
        items.push(Property::new(
            tr!("address_details__derivation_path"),
            path,
            false,
        ))
    });

    items
}

pub(crate) fn confirm_typed_data_final() -> Result<()> {
    match ui::confirm_action(
        tr!("ethereum__title_confirm_typed_data"),
        tr!("ethereum__sign_eip712"),
        None,
        None,
        true,
        Some(tr!("buttons__hold_to_confirm")),
        true,
        Some("confirm_typed_data_final"),
        ButtonRequestType::ButtonRequestOther.into(),
        false,
    )? {
        ui::TrezorUiResult::Confirmed => Ok(()),
        _ => Err(Error::Cancelled),
    }
}

pub(crate) fn confirm_empty_typed_message() -> Result<()> {
    confirm_text(
        "confirm_empty_typed_message",
        tr!("ethereum__title_confirm_message"),
        "",
        Some(tr!("ethereum__no_message_field")),
        ButtonRequestType::ButtonRequestOther.into(),
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

pub(crate) fn should_show_domain(name: &[u8], version: &[u8]) -> Result<bool> {
    let domain_name = decode_typed_data(name, "string")?;
    let domain_version = decode_typed_data(version, "string")?;

    let para = [
        StrExt::new(tr!("ethereum__name_and_version"), false),
        StrExt::new(&domain_name, false),
        StrExt::new(&domain_version, false),
    ];

    let result = ui::should_show_more(
        tr!("ethereum__title_confirm_domain"),
        &para,
        tr!("ethereum__show_full_domain"),
        Some("should_show_domain"),
        ButtonRequestType::ButtonRequestOther.into(),
        tr!("buttons__confirm"),
    )
    .map_err(|_| Error::Cancelled)?;
    Ok(result)
}

pub(crate) fn should_show_struct(
    description: &str,
    data_members: &[StructMember],
    title: Option<&str>,
    button_text: Option<&str>,
) -> Result<bool> {
    let title = title.unwrap_or(tr!("ethereum__title_confirm_struct"));
    let button_text = button_text.unwrap_or(tr!("ethereum__show_full_struct"));

    // TODO: implement plural form
    let contains = uformat!("Contains {} keys", data_members.len());

    let field_names = data_members
        .iter()
        .map(|field| field.name.as_str())
        .collect::<Vec<_>>()
        .join(", ");

    let para = [
        StrExt::new(description, false),
        StrExt::new(&contains, false),
        StrExt::new(&field_names, false),
    ];

    ui::should_show_more(
        title,
        &para,
        button_text,
        Some("should_show_struct"),
        ButtonRequestType::ButtonRequestOther.into(),
        tr!("buttons__confirm"),
    )
    .map_err(|_| Error::Cancelled)
}

pub(crate) fn should_show_array(
    parent_objects: &[&str],
    data_type: &str,
    size: u32,
) -> Result<bool> {
    // Leaving english plural form because of dynamic noun - data_type
    let array_of_plural = uformat!(
        "{} {}",
        tr!("words__array_of"),
        format_plural_english(size, data_type).as_str()
    );
    let para = [StrExt::new(&array_of_plural, false)];
    ui::should_show_more(
        &limit_str(&parent_objects.to_vec().join("."), None),
        &para,
        tr!("ethereum__show_full_array"),
        Some("should_show_array"),
        ButtonRequestType::ButtonRequestOther.into(),
        tr!("buttons__confirm"),
    )
    .map_err(|_| Error::Cancelled)
}

pub(crate) fn confirm_typed_value(
    name: &str,
    value: &[u8],
    parent_objects: &[&str],
    field: &FieldType,
    array_idx: Option<u32>,
) -> Result<()> {
    let type_name = get_type_name(field)?;
    let mut parts: Vec<&str> = parent_objects.to_vec();

    let (title, description) = if let Some(idx) = array_idx {
        parts.push(name);
        (
            limit_str(&parts.join("."), None),
            uformat!("[{}] ({})", idx, type_name.as_str()),
        )
    } else {
        (
            limit_str(&parts.join("."), None),
            uformat!("{} ({})", name, type_name.as_str()),
        )
    };

    let data = decode_typed_data(value, &type_name)?;
    let br_name = "confirm_typed_value";
    let br_code = ButtonRequestType::ButtonRequestOther.into();

    if field.data_type == DataType::Address as i32 || field.data_type == DataType::Bytes as i32 {
        confirm_blob(
            &title,
            &data,
            Some(&description),
            None,
            br_name,
            br_code,
            false,
            None,
            None,
            false,
            false,
            true,
        )?;
    } else {
        confirm_text(br_name, &title, &data, Some(&description), br_code)?;
    }

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
        }
    }

    let title = "Confirm message";
    let br_code = ButtonRequestType::ButtonRequestOther.into();
    let hold = !verify;
    if message.chars().count() > LONG_MSG_PAGE_THRESHOLD {
        confirm_blob(
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

/// Keep "0x" prefix in a separate chunk (#6601).
pub(crate) fn addr_pad(addr: &str, chunkify: bool) -> String {
    assert!(addr.starts_with("0x"));
    let mut addr = addr.to_string();
    if chunkify {
        addr = uformat!("  {}", addr.as_str());
    }
    addr
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
            ui::confirm_value(
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
            )
        },
        &menu,
        br_name,
    )?)?;
    Ok(())
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
                ui::confirm_value_intro(
                    title,
                    &data[..data.len().min(170)], /* TODO: be precise about the 1 st page */
                    description,
                    verb,
                    verb_cancel,
                    hold,
                    chunkify,
                    name,
                    br_code,
                )
            },
            |name| {
                ui::confirm_value(
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
                )
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

//! Confirmation screens, ported from Core's `apps/stellar/layout.py` and the
//! shared `confirm_*` helpers of the Eckhart layouts they are built on.

use crate::{
    alloc_types::{String, ToString, Vec, vec},
    consts::{NETWORK_PASSPHRASE_FUTURENET, NETWORK_PASSPHRASE_PUBLIC, NETWORK_PASSPHRASE_TESTNET},
    helpers::contract_address_from_address,
    paths::{Bip32Path, PATTERNS_ADDRESS},
    proto::{
        common::{PaymentRequest, button_request::ButtonRequestType},
        stellar::{
            Asset, CreateContractArgsV2, InvokeContractArgs, ScVal, SorobanAuthorizedInvocation,
            contract_executable::ContractExecutableType,
            contract_id_preimage::ContractIdPreimageType,
            sc_val::{
                Int128Parts, Int256Parts, ScValMapEntry, ScValType, UInt128Parts, UInt256Parts,
            },
            sign_tx::MemoType,
            soroban_authorized_function::SorobanAuthorizedFunctionType,
        },
    },
    strutil::{format_duration, format_timestamp, hex_encode},
    tokens::{StellarToken, resolve_sep41_token},
    uformat,
};
use primitive_types::U256;
use trezor_app_sdk::{
    Error, Result, ResultExt,
    ui::{self, ConfirmValue, Property, StrExt},
};

use crate::consts::{COIN, SLIP44_ID};

fn br(code: ButtonRequestType) -> i32 {
    code as i32
}

/// Fills the `{0}` placeholder of a translation template.
pub(crate) fn fill(template: &str, arg: &str) -> String {
    template.replace("{0}", arg)
}

// ---------------------------------------------------------------------------
// Shared building blocks (the Eckhart `confirm_*` helpers)
// ---------------------------------------------------------------------------

/// General confirmation dialog, used by many other confirm_* functions.
///
/// Additional details (`info_items`) are reachable from the screen's menu.
#[allow(clippy::too_many_arguments)]
pub(crate) fn confirm_value(
    title: &str,
    value: &str,
    description: Option<&str>,
    br_name: &str,
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

    ui::error_if_not_confirmed(
        ui::interact_with_menu_flow(
            |name| {
                ui::confirm_value(ConfirmValue::new(
                    title,
                    value,
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
            Some(br_name),
        )
        .c()?,
    )
    .c()
}

/// Confirms a plain (non-data) value with a "Continue" button.
pub(crate) fn confirm_plain_value(
    title: &str,
    value: &str,
    description: Option<&str>,
    br_name: &str,
) -> Result<()> {
    confirm_value(
        title,
        value,
        description,
        br_name,
        br(ButtonRequestType::Other),
        false,
        Some(tr!("buttons__continue")),
        None,
        false,
        false,
        None,
        None,
        None,
    )
}

#[allow(clippy::too_many_arguments)]
pub(crate) fn confirm_address_full(
    title: &str,
    address: &str,
    subtitle: Option<&str>,
    description: Option<&str>,
    verb: Option<&str>,
    br_name: &str,
    br_code: i32,
    info_items: Option<&[Property]>,
    info_title: Option<&str>,
) -> Result<()> {
    confirm_value(
        title,
        address,
        description,
        br_name,
        br_code,
        true,
        verb,
        subtitle,
        false,
        true,
        info_items,
        info_title,
        None,
    )
}

/// Confirms an address, with a "Continue" button when `with_continue` is set.
pub(crate) fn confirm_address(
    title: &str,
    address: &str,
    description: Option<&str>,
    br_name: &str,
    with_continue: bool,
) -> Result<()> {
    confirm_address_full(
        title,
        address,
        None,
        description,
        with_continue.then_some(tr!("buttons__continue")),
        br_name,
        br(ButtonRequestType::Other),
        None,
        None,
    )
}

fn confirm_text(br_name: &str, title: &str, data: &str, description: Option<&str>) -> Result<()> {
    confirm_value(
        title,
        data,
        description,
        br_name,
        br(ButtonRequestType::Other),
        true,
        None,
        None,
        false,
        false,
        None,
        None,
        None,
    )
}

pub(crate) fn confirm_properties(
    br_name: &str,
    title: &str,
    props: &[Property],
    subtitle: Option<&str>,
    verb: Option<&str>,
) -> Result<()> {
    let menu = ui::Menu::new(&[], Some(ui::Cancel::new(tr!("buttons__cancel"))));
    ui::error_if_not_confirmed(
        ui::interact_with_menu_flow(
            |name| {
                ui::confirm_properties(ui::ConfirmProperties::new(
                    title,
                    props,
                    subtitle,
                    verb,
                    false,
                    name,
                    br(ButtonRequestType::ConfirmOutput),
                ))
            },
            &menu,
            Some(br_name),
        )
        .c()?,
    )
    .c()
}

fn show_warning(br_name: &str, content: &str, code: ButtonRequestType) -> Result<()> {
    ui::show_warning(ui::ShowWarning::new(
        tr!("words__important"),
        content,
        tr!("buttons__continue_anyway"),
        Some(br_name),
        br(code),
        true,
        true,
    ))
    .c()
}

fn account_name_and_path(address_n: &[u32]) -> Result<(String, String)> {
    let dp = Bip32Path::from_slice(address_n);
    let account_name = dp
        .get_account_name(COIN, &PATTERNS_ADDRESS, SLIP44_ID)
        .ok_or(Error::DataError("Stellar: Invalid account name"))?;
    Ok((account_name, dp.format_path()))
}

// ---------------------------------------------------------------------------
// Transaction level
// ---------------------------------------------------------------------------

pub fn require_confirm_tx_source(tx_source: &str) -> Result<()> {
    show_warning(
        "confirm_tx_source",
        tr!("stellar__transaction_source_diff_warning"),
        ButtonRequestType::Warning,
    )
    .c()?;

    confirm_address_full(
        tr!("stellar__transaction_source"),
        tx_source,
        None,
        None,
        Some(tr!("buttons__continue")),
        "confirm_tx_source",
        br(ButtonRequestType::ConfirmOutput),
        None,
        None,
    )
}

pub fn require_confirm_memo(memo_type: MemoType, memo_text: &str) -> Result<()> {
    let description = match memo_type {
        MemoType::Text => "Memo (TEXT)",
        MemoType::Id => "Memo (ID)",
        MemoType::Hash => "Memo (HASH)",
        MemoType::Return => "Memo (RETURN)",
        MemoType::None => {
            return show_warning(
                "confirm_memo",
                tr!("stellar__exchanges_require_memo"),
                ButtonRequestType::Warning,
            );
        }
    };

    confirm_value(
        tr!("stellar__confirm_memo"),
        memo_text,
        Some(description),
        "confirm_memo",
        br(ButtonRequestType::ConfirmOutput),
        false,
        Some(tr!("buttons__continue")),
        None,
        false,
        false,
        None,
        None,
        None,
    )
}

pub(crate) struct Refund {
    pub address: String,
    pub account_path: Option<String>,
}

pub(crate) struct Trade {
    pub sell_amount: String,
    pub buy_amount: String,
    pub address: String,
    pub account_path: Option<String>,
}

/// Total amount of a verified payment request, formatted in the asset it is
/// denominated in.
pub fn require_confirm_payment_request(
    provider_address: &str,
    payment_request: &PaymentRequest,
    address_n: &[u32],
    total_amount: &StellarToken,
    amount: u128,
) -> Result<()> {
    let total_amount = total_amount.format(amount);

    let mut texts: Vec<(Option<&str>, &str)> = Vec::new();
    let mut refunds = Vec::new();
    let mut trades = Vec::new();
    for memo in &payment_request.memos {
        if let Some(text_memo) = &memo.text_memo {
            texts.push((None, text_memo.text.as_str()));
        } else if let Some(text_details_memo) = &memo.text_details_memo {
            texts.push((
                Some(text_details_memo.title.as_str()),
                text_details_memo.text.as_str(),
            ));
        } else if let Some(refund_memo) = &memo.refund_memo {
            refunds.push(Refund {
                address: refund_memo.address.clone(),
                account_path: Some(Bip32Path::from_slice(&refund_memo.address_n).format_path()),
            });
        } else if let Some(coin_purchase_memo) = &memo.coin_purchase_memo {
            trades.push(Trade {
                sell_amount: uformat!("-\u{a0}{}", total_amount.as_str()),
                buy_amount: uformat!("+\u{a0}{}", coin_purchase_memo.amount.as_str()),
                address: coin_purchase_memo.address.clone(),
                account_path: Some(
                    Bip32Path::from_slice(&coin_purchase_memo.address_n).format_path(),
                ),
            });
        } else {
            return Err(Error::DataError(
                "Unrecognized memo type in payment request memo.",
            ));
        }
    }

    let account_path = if address_n.is_empty() {
        None
    } else {
        Some(Bip32Path::from_slice(address_n).format_path())
    };
    let account_items: Vec<Property> = account_path
        .as_deref()
        .map(|path| {
            vec![Property::new(
                tr!("address_details__derivation_path"),
                path,
                false,
            )]
        })
        .unwrap_or_default();

    confirm_payment_request(
        &payment_request.recipient_name,
        provider_address,
        &texts,
        &refunds,
        &trades,
        &account_items,
    )
}

fn confirm_payment_request(
    recipient_name: &str,
    recipient_address: &str,
    texts: &[(Option<&str>, &str)],
    refunds: &[Refund],
    trades: &[Trade],
    account_items: &[Property],
) -> Result<()> {
    let is_swap = !trades.is_empty();
    let (title, _summary_title) = if is_swap {
        (tr!("words__swap"), tr!("words__swap"))
    } else {
        (tr!("buttons__confirm"), tr!("words__title_summary"))
    };

    for (text_title, text) in texts {
        ui::error_if_not_confirmed(ui::confirm_value(ConfirmValue::new(
            text_title.unwrap_or(title),
            text,
            None,
            Some("confirm_payment_request"),
            br(ButtonRequestType::Other),
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
        ))?)?;
    }

    let provider_props = [Property::new("", recipient_address, true)];
    let mut menu_items = Vec::with_capacity(1 + refunds.len());
    menu_items.push(ui::Details::new(
        tr!("address__title_provider_address"),
        &provider_props,
        None,
        None,
        br(ButtonRequestType::Other),
    ));

    let refund_props: Vec<Vec<Property>> = refunds
        .iter()
        .map(|refund| {
            let mut props = vec![Property::new("", refund.address.as_str(), false)];
            if let Some(path) = &refund.account_path {
                props.push(Property::new(
                    tr!("address_details__derivation_path"),
                    path.as_str(),
                    true,
                ));
            }
            props
        })
        .collect();
    for props in &refund_props {
        menu_items.push(ui::Details::new(
            tr!("address__title_refund_address"),
            props.as_slice(),
            None,
            None,
            br(ButtonRequestType::Other),
        ));
    }

    let menu = ui::Menu::new(&menu_items, Some(ui::Cancel::new(tr!("send__cancel_sign"))));

    ui::error_if_not_confirmed(ui::interact_with_menu_flow(
        |name| {
            ui::confirm_value(ConfirmValue::new(
                title,
                recipient_name,
                None,
                name,
                br(ButtonRequestType::Other),
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
            ))
        },
        &menu,
        Some("confirm_payment_request"),
    )?)?;

    for trade in trades {
        trade_flow(title, tr!("words__assets"), trade, account_items)?;
    }
    Ok(())
}

fn trade_flow(
    title: &str,
    subtitle: &str,
    trade: &Trade,
    account_items: &[Property],
) -> Result<()> {
    let mut account_properties = Vec::with_capacity(2);
    account_properties.push(Property::new("", trade.address.as_str(), true));
    if let Some(path) = &trade.account_path {
        account_properties.push(Property::new(
            tr!("address_details__derivation_path"),
            path.as_str(),
            true,
        ));
    }
    account_properties.extend_from_slice(account_items);

    let menu_items = [ui::Details::new(
        tr!("address__title_receive_address"),
        &account_properties,
        None,
        Some(tr!("send__send_from")),
        br(ButtonRequestType::Other),
    )];
    let menu = ui::Menu::new(&menu_items, Some(ui::Cancel::new(tr!("send__cancel_sign"))));

    ui::error_if_not_confirmed(ui::interact_with_menu_flow(
        |name| {
            ui::confirm_trade(ui::ConfirmTrade::new(
                title,
                subtitle,
                &trade.buy_amount,
                Some(&trade.sell_amount),
                false,
                name,
                br(ButtonRequestType::Other),
            ))
        },
        &menu,
        Some("confirm_trade"),
    )?)
}

fn get_network_name(network_passphrase: &str) -> String {
    match network_passphrase {
        NETWORK_PASSPHRASE_PUBLIC => String::from("Mainnet"),
        NETWORK_PASSPHRASE_TESTNET => String::from("Testnet"),
        NETWORK_PASSPHRASE_FUTURENET => String::from("Futurenet"),
        other => uformat!("Unknown ({})", other),
    }
}

fn format_bound(timestamp: u32) -> String {
    if timestamp > 0 {
        format_timestamp(timestamp as u64).unwrap_or_else(|| timestamp.to_string())
    } else {
        String::from(tr!("stellar__no_restriction"))
    }
}

pub fn confirm_tx_final(
    address_n: &[u32],
    fee: u32,
    timebounds: (u32, u32),
    is_sending_from_trezor_account: bool,
    network_passphrase: &str,
) -> Result<()> {
    let (timebounds_start, timebounds_end) = timebounds;
    let valid_from = format_bound(timebounds_start);
    let valid_to = format_bound(timebounds_end);
    let network = get_network_name(network_passphrase);
    let extra_items = [
        Property::plain(tr!("stellar__valid_from"), &valid_from),
        Property::plain(tr!("stellar__valid_to"), &valid_to),
        Property::plain(tr!("words__network"), &network),
    ];

    let (account_name, account_path) = account_name_and_path(address_n).c()?;
    let account_items = [
        Property::plain(tr!("words__account"), &account_name),
        Property::plain(tr!("address_details__derivation_path"), &account_path),
    ];

    // the fee is always in XLM
    let fee = StellarToken::native().format(fee as u128);

    ui::error_if_not_confirmed(
        ui::confirm_summary(ui::ConfirmSummary::new(
            tr!("words__send"),
            None,
            None,
            &fee,
            tr!("send__maximum_fee"),
            Some(if is_sending_from_trezor_account {
                tr!("send__send_from")
            } else {
                tr!("stellar__sign_with")
            }),
            Some(&account_items),
            None,
            Some(&extra_items),
            false,
            Some("confirm_stellar_tx"),
            br(ButtonRequestType::SignTx),
        ))
        .c()?,
    )
    .c()
}

// ---------------------------------------------------------------------------
// Soroban authorization signing
// ---------------------------------------------------------------------------

/// Confirms the device account whose key signs the Soroban authorization.
///
/// Always the first screen of the flow, like the signing address screen of
/// Ethereum's message signing flows.
pub fn require_confirm_auth_signing_address(address: &str, address_n: &[u32]) -> Result<()> {
    let (account_name, account_path) = account_name_and_path(address_n).c()?;
    let info_items = [
        Property::plain(tr!("words__account"), &account_name),
        Property::plain(tr!("address_details__derivation_path"), &account_path),
    ];

    confirm_address_full(
        tr!("sign_message__confirm_address"),
        address,
        None,
        None,
        Some(tr!("buttons__continue")),
        "confirm_auth_signing_address",
        br(ButtonRequestType::ConfirmOutput),
        Some(&info_items),
        Some(tr!("address_details__account_info")),
    )
}

/// Confirms the address whose Soroban authorization credentials are signed.
///
/// Only shown when it differs from the signing address, i.e. when the device
/// account signs on behalf of another party, e.g. a contract account of which
/// the device account is a signer.
pub fn require_confirm_auth_on_behalf_of(address: &str) -> Result<()> {
    confirm_address_full(
        tr!("words__authorization"),
        address,
        None,
        Some(tr!("stellar__on_behalf_of")),
        Some(tr!("buttons__continue")),
        "confirm_auth_on_behalf_of",
        br(ButtonRequestType::ConfirmOutput),
        None,
        None,
    )
}

pub fn confirm_auth_final(
    signature_expiration_ledger: u32,
    network_passphrase: &str,
) -> Result<()> {
    let network = get_network_name(network_passphrase);
    let ledger = signature_expiration_ledger.to_string();
    confirm_value(
        tr!("stellar__sign_authorization"),
        &ledger,
        Some(tr!("stellar__valid_until_ledger")),
        "confirm_soroban_auth",
        br(ButtonRequestType::SignTx),
        false,
        None,
        None,
        true,
        false,
        Some(&[Property::plain(tr!("words__network"), &network)]),
        None,
        None,
    )
}

// ---------------------------------------------------------------------------
// Contract calls
// ---------------------------------------------------------------------------

/// Confirms a contract call using the generic, unparsed arguments UI.
///
/// `authorization_title` is omitted for the function invoked directly by a
/// transaction. For an authorization-tree node, it identifies the node while
/// each screen's usual title moves into its description or subtitle.
fn confirm_invoke_contract_args(
    args: &InvokeContractArgs,
    br_name_prefix: &str,
    authorization_title: Option<&str>,
) -> Result<()> {
    confirm_address_full(
        authorization_title.unwrap_or(tr!("stellar__invoke_contract")),
        &args.contract_address,
        None,
        authorization_title.map(|_| tr!("stellar__invoke_contract")),
        None,
        &uformat!("{}_contract_address", br_name_prefix),
        br(ButtonRequestType::Other),
        None,
        None,
    )
    .c()?;
    confirm_text(
        &uformat!("{}_function", br_name_prefix),
        authorization_title.unwrap_or(tr!("words__function")),
        &args.function_name,
        authorization_title.map(|_| tr!("words__function")),
    )
    .c()?;
    confirm_args(&args.args, br_name_prefix, authorization_title)
}

/// Confirms the arguments of a call, if any, one formatted value each.
fn confirm_args(
    args: &[ScVal],
    br_name_prefix: &str,
    authorization_title: Option<&str>,
) -> Result<()> {
    if args.is_empty() {
        return Ok(());
    }
    let keys: Vec<String> = (0..args.len())
        .map(|i| uformat!("{} / {}", i + 1, args.len()))
        .collect();
    let values = args
        .iter()
        .map(format_sc_val)
        .collect::<Result<Vec<String>>>()
        .c()?;
    let props: Vec<Property> = keys
        .iter()
        .zip(values.iter())
        .map(|(key, value)| Property::mono(key, value))
        .collect();

    let menu = ui::Menu::new(&[], Some(ui::Cancel::new(tr!("buttons__cancel"))));
    ui::error_if_not_confirmed(
        ui::interact_with_menu_flow(
            |name| {
                ui::confirm_properties(ui::ConfirmProperties::new(
                    authorization_title.unwrap_or(tr!("words__arguments")),
                    &props,
                    authorization_title.map(|_| tr!("words__arguments")),
                    None,
                    false,
                    name,
                    br(ButtonRequestType::ConfirmOutput),
                ))
            },
            &menu,
            Some(&uformat!("{}_args", br_name_prefix)),
        )
        .c()?,
    )
    .c()
}

// SEP-41 token functions given a dedicated UI, see
// https://github.com/stellar/stellar-protocol/blob/master/ecosystem/sep-0041.md
const SEP41_TRANSFER: &str = "transfer";
const SEP41_APPROVE: &str = "approve";

/// Reads a SEP-41 `transfer(from, to, amount)` call.
fn parse_sep41_transfer(args: &InvokeContractArgs) -> Option<(&str, &str, u128)> {
    if args.function_name != SEP41_TRANSFER || args.args.len() != 3 {
        return None;
    }
    Some((
        sc_address(&args.args[0])?,
        sc_address(&args.args[1])?,
        sc_amount(&args.args[2])?,
    ))
}

/// Reads a SEP-41 `approve(from, spender, amount, live_until_ledger)` call.
fn parse_sep41_approve(args: &InvokeContractArgs) -> Option<(&str, &str, u128, u32)> {
    if args.function_name != SEP41_APPROVE || args.args.len() != 4 {
        return None;
    }
    Some((
        sc_address(&args.args[0])?,
        sc_address(&args.args[1])?,
        sc_amount(&args.args[2])?,
        sc_u32(&args.args[3])?,
    ))
}

fn sc_type(val: &ScVal) -> Option<ScValType> {
    ScValType::try_from(val.r#type).ok()
}

fn sc_address(val: &ScVal) -> Option<&str> {
    if sc_type(val)? != ScValType::ScvAddress {
        return None;
    }
    val.address.as_deref()
}

/// Reads an amount suitable for the dedicated token UI.
///
/// Stellar Asset Contracts reject negative amounts. Custom SEP-41 contracts
/// may accept them, but such calls are deliberately left to the raw contract
/// flow instead of being presented as regular token operations.
fn sc_amount(val: &ScVal) -> Option<u128> {
    if sc_type(val)? != ScValType::ScvI128 {
        return None;
    }
    let amount = i128_value(val.i128.as_ref()?);
    u128::try_from(amount).ok()
}

fn sc_u32(val: &ScVal) -> Option<u32> {
    if sc_type(val)? != ScValType::ScvU32 {
        return None;
    }
    val.u32
}

/// Confirms a contract call, using the dedicated token UI when possible.
///
/// `authorization_title` is omitted for the host function invoked directly by
/// a transaction; transfers then retain the standard payment-style output
/// screen. An invocation from either kind of authorization tree provides a
/// title identifying the node, and the token action becomes its subtitle.
///
/// `authorizing_address` is used in both contexts to avoid repeating the
/// address that already authorizes the transaction operation or the whole
/// authorization tree.
pub fn confirm_invoke_contract(
    args: &InvokeContractArgs,
    network_id: &[u8; 32],
    authorizing_address: &str,
    authorization_title: Option<&str>,
) -> Result<()> {
    let br_name_prefix = if authorization_title.is_none() {
        "op_invoke"
    } else {
        "op_auth"
    };

    if let Some(token) = resolve_sep41_token(args, network_id) {
        if let Some(transfer) = parse_sep41_transfer(args) {
            return confirm_sep41_transfer(
                transfer,
                &token,
                &args.contract_address,
                authorizing_address,
                br_name_prefix,
                authorization_title,
            );
        }
        if let Some(approve) = parse_sep41_approve(args) {
            return confirm_sep41_approve(
                approve,
                &token,
                &args.contract_address,
                authorizing_address,
                br_name_prefix,
                authorization_title,
            );
        }
    }

    confirm_invoke_contract_args(args, br_name_prefix, authorization_title)
}

/// Confirms a parsed SEP-41 transfer using its dedicated token UI.
fn confirm_sep41_transfer(
    (from_address, to_address, amount): (&str, &str, u128),
    token: &StellarToken,
    token_contract: &str,
    authorizing_address: &str,
    br_name_prefix: &str,
    authorization_title: Option<&str>,
) -> Result<()> {
    // Without an authorization title, this is the transaction's own action and
    // is framed like a classic payment. A tree node instead describes what a
    // signature permits and may belong to another party altogether, so it gets
    // a neutral, perspective-free label, in line with "Approve token".
    let action = if authorization_title.is_none() {
        tr!("words__send")
    } else {
        tr!("stellar__transfer_token")
    };
    let screen_title = authorization_title.unwrap_or(action);
    // For a direct transaction, "Send" is the title and `confirm_stellar_output`
    // supplies the recipient context. In an authorization tree, its node title
    // is retained and the action is shown as the subtitle.
    let subtitle = if authorization_title.is_none() {
        ""
    } else {
        action
    };

    if from_address != authorizing_address {
        confirm_stellar_address(
            screen_title,
            subtitle,
            from_address,
            tr!("stellar__from"),
            &uformat!("{}_from", br_name_prefix),
        )
        .c()?;
    }

    if authorization_title.is_some() {
        confirm_stellar_address(
            screen_title,
            subtitle,
            to_address,
            tr!("stellar__to"),
            &uformat!("{}_to", br_name_prefix),
        )
        .c()?;
        confirm_stellar_output_amount(
            screen_title,
            subtitle,
            &token.format(amount),
            token,
            Some(tr!("words__amount")),
            Some(token_contract),
        )
    } else {
        confirm_stellar_output(
            to_address,
            &token.format(amount),
            0, // a Soroban operation is always the only one
            token,
            None,
            None,
            Some(token_contract),
        )
    }
}

/// Confirms a parsed SEP-41 approval or revocation using its dedicated UI.
fn confirm_sep41_approve(
    (from_address, spender, amount, live_until_ledger): (&str, &str, u128, u32),
    token: &StellarToken,
    token_contract: &str,
    authorizing_address: &str,
    br_name_prefix: &str,
    authorization_title: Option<&str>,
) -> Result<()> {
    let action = if amount == 0 {
        tr!("stellar__revoke_approval")
    } else {
        tr!("stellar__approve_token")
    };
    let screen_title = authorization_title.unwrap_or(action);
    let subtitle = if authorization_title.is_none() {
        ""
    } else {
        action
    };

    if from_address != authorizing_address {
        confirm_stellar_address(
            screen_title,
            subtitle,
            from_address,
            tr!("stellar__from"),
            &uformat!("{}_from", br_name_prefix),
        )
        .c()?;
    }
    confirm_stellar_address(
        screen_title,
        subtitle,
        spender,
        tr!("stellar__spender"),
        &uformat!("{}_spender", br_name_prefix),
    )
    .c()?;

    let (display_value, value_label) = if amount == 0 {
        // "Revoke approval" already communicates the zero allowance, so
        // identify the token instead of displaying the omitted amount.
        (token.symbol.clone(), tr!("words__token"))
    } else {
        (token.format(amount), tr!("words__amount"))
    };
    confirm_stellar_output_amount(
        screen_title,
        subtitle,
        &display_value,
        token,
        Some(value_label),
        Some(token_contract),
    )
    .c()?;
    confirm_stellar_valid_until(
        screen_title,
        subtitle,
        live_until_ledger,
        &uformat!("{}_valid_until", br_name_prefix),
    )
}

// ---------------------------------------------------------------------------
// The Stellar specific helpers of the Eckhart layouts
// ---------------------------------------------------------------------------

fn non_empty(s: &str) -> Option<&str> {
    (!s.is_empty()).then_some(s)
}

pub(crate) fn confirm_stellar_address(
    title: &str,
    subtitle: &str,
    address: &str,
    description: &str,
    br_name: &str,
) -> Result<()> {
    confirm_address_full(
        title,
        address,
        non_empty(subtitle),
        Some(description),
        Some(tr!("buttons__continue")),
        br_name,
        br(ButtonRequestType::Other),
        None,
        None,
    )
}

pub(crate) fn confirm_stellar_valid_until(
    title: &str,
    subtitle: &str,
    live_until_ledger: u32,
    br_name: &str,
) -> Result<()> {
    confirm_value(
        title,
        &live_until_ledger.to_string(),
        Some(tr!("stellar__valid_until_ledger")),
        br_name,
        br(ButtonRequestType::Other),
        false,
        Some(tr!("buttons__continue")),
        non_empty(subtitle),
        false,
        false,
        None,
        None,
        None,
    )
}

pub(crate) fn confirm_stellar_output_amount(
    title: &str,
    subtitle: &str,
    amount: &str,
    token: &StellarToken,
    description: Option<&str>,
    token_contract: Option<&str>,
) -> Result<()> {
    let issuer_label = token
        .issuer
        .as_ref()
        .map(|_| fill(tr!("stellar__issuer_template"), &token.symbol));

    let mut info_items: Vec<Property> = Vec::with_capacity(2);
    if let (Some(label), Some(issuer)) = (&issuer_label, &token.issuer) {
        info_items.push(Property::plain(label, issuer));
    }
    if let Some(contract) = token_contract.filter(|c| !c.is_empty()) {
        info_items.push(Property::plain(tr!("stellar__token_contract"), contract));
    }

    confirm_value(
        title,
        amount,
        Some(description.unwrap_or("")),
        "confirm_output_amount",
        br(ButtonRequestType::ConfirmOutput),
        false,
        Some(tr!("buttons__continue")),
        non_empty(subtitle),
        false,
        false,
        (!info_items.is_empty()).then_some(info_items.as_slice()),
        Some(tr!("stellar__token_info")),
        None,
    )
}

pub(crate) fn confirm_stellar_output(
    address: &str,
    amount: &str,
    output_index: usize,
    token: &StellarToken,
    address_description: Option<&str>,
    amount_description: Option<&str>,
    token_contract: Option<&str>,
) -> Result<()> {
    let subtitle = uformat!("{} #{}", tr!("words__recipient"), output_index + 1);
    confirm_address_full(
        tr!("words__address"),
        address,
        Some(&subtitle),
        address_description,
        Some(tr!("buttons__continue")),
        "confirm_output_address",
        br(ButtonRequestType::ConfirmOutput),
        None,
        None,
    )
    .c()?;

    confirm_stellar_output_amount(
        tr!("words__send"),
        &subtitle,
        amount,
        token,
        Some(amount_description.unwrap_or(tr!("words__amount"))),
        token_contract,
    )
}

// ---------------------------------------------------------------------------
// Contract creation and authorization trees
// ---------------------------------------------------------------------------

/// Confirms the creation of a contract, i.e. a deployment.
///
/// The new contract is identified by its address, which is derived from the
/// contract ID preimage (CAP-46-02) and so commits to the deployer and salt.
/// Neither is shown on its own: in Soroban the deployer gains no rights over
/// the contract, and it has to authorize the creation anyway. Then the Wasm
/// the contract runs and the arguments of its constructor are confirmed.
///
/// `authorization_title` is used like in [`confirm_invoke_contract`].
pub fn confirm_create_contract(
    args: &CreateContractArgsV2,
    network_id: &[u8; 32],
    authorization_title: Option<&str>,
) -> Result<()> {
    let preimage = &args.contract_id_preimage;
    let executable = &args.executable;
    if ContractIdPreimageType::try_from(preimage.r#type).ok()
        != Some(ContractIdPreimageType::ContractIdPreimageFromAddress)
    {
        return Err(Error::DataError(
            "Stellar: unsupported contract ID preimage type",
        ));
    }
    if ContractExecutableType::try_from(executable.r#type).ok()
        != Some(ContractExecutableType::ContractExecutableWasm)
    {
        return Err(Error::DataError(
            "Stellar: unsupported contract executable type",
        ));
    }
    let from_address = preimage
        .from_address
        .as_ref()
        .ok_or(Error::DataError("Stellar: missing from_address"))?;
    let wasm_hash = executable
        .wasm_hash
        .as_ref()
        .ok_or(Error::DataError("Stellar: missing wasm_hash"))?;

    let br_name_prefix = if authorization_title.is_none() {
        "op_create"
    } else {
        "op_auth"
    };
    let title = authorization_title.unwrap_or(tr!("stellar__deploy_contract"));

    let contract_address =
        contract_address_from_address(network_id, &from_address.address, &from_address.salt).c()?;
    confirm_address_full(
        title,
        &contract_address,
        None,
        authorization_title.map(|_| tr!("stellar__deploy_contract")),
        None,
        &uformat!("{}_contract_address", br_name_prefix),
        br(ButtonRequestType::Other),
        None,
        None,
    )
    .c()?;
    confirm_value(
        title,
        &hex_encode(wasm_hash).map_err(|_| Error::DataError("Stellar: invalid wasm_hash"))?,
        Some(tr!("stellar__wasm_hash")),
        &uformat!("{}_wasm_hash", br_name_prefix),
        br(ButtonRequestType::Other),
        true,
        Some(tr!("buttons__continue")),
        None,
        false,
        false,
        None,
        None,
        None,
    )
    .c()?;
    confirm_args(&args.constructor_args, br_name_prefix, authorization_title)
}

/// Confirms a standalone authorized invocation tree (auth entry signing).
///
/// Unlike in a transaction, there is always exactly one entry being signed, so
/// its root label is empty; sub-invocations are numbered relative to it
/// (".1", ".1.2", ...), the same paths they would have inside a transaction.
pub fn confirm_authorized_invocation(
    invocation: &SorobanAuthorizedInvocation,
    network_id: &[u8; 32],
    authorizing_address: &str,
) -> Result<()> {
    confirm_invocation(invocation, "", network_id, authorizing_address, false)
}

/// Confirms an authorized invocation and its sub-invocations recursively.
///
/// The whole authorization tree is shown by default (it is security-critical
/// and can differ from the host function being invoked). `position` is the
/// root label plus the dot-delimited path in the auth tree (e.g. "#2", "#2.1"
/// in a transaction), or empty for the unlabeled root of a standalone
/// authorization entry (whose children are then ".1", ".1.2", ...), so a given
/// entry's children carry the same paths in both flows. `authorizing_address`
/// belongs to the whole tree and is propagated unchanged to every child.
pub fn confirm_invocation(
    invocation: &SorobanAuthorizedInvocation,
    position: &str,
    network_id: &[u8; 32],
    authorizing_address: &str,
    is_root: bool,
) -> Result<()> {
    let authorization_title = if position.is_empty() {
        String::from(tr!("words__authorization"))
    } else {
        uformat!("{} {}", tr!("words__authorization"), position)
    };

    let func = &invocation.function;
    match SorobanAuthorizedFunctionType::try_from(func.r#type) {
        Ok(SorobanAuthorizedFunctionType::ContractFn) => {
            let contract_fn = func
                .contract_fn
                .as_ref()
                .ok_or(Error::DataError("Stellar: missing contract_fn"))?;
            if !is_root {
                confirm_invoke_contract(
                    contract_fn,
                    network_id,
                    authorizing_address,
                    Some(&authorization_title),
                )
                .c()?;
            }
        }
        Ok(SorobanAuthorizedFunctionType::CreateContractV2HostFn) => {
            let create = func
                .create_contract_v2_host_fn
                .as_ref()
                .ok_or(Error::DataError(
                    "Stellar: missing create_contract_v2_host_fn",
                ))?;
            if !is_root {
                confirm_create_contract(create, network_id, Some(&authorization_title)).c()?;
            }
        }
        Err(_) => {
            return Err(Error::DataError(
                "Stellar: unsupported authorized function type",
            ));
        }
    }

    for (i, sub) in invocation.sub_invocations.iter().enumerate() {
        confirm_invocation(
            sub,
            &uformat!("{}.{}", position, i + 1),
            network_id,
            authorizing_address,
            false,
        )
        .c()?;
    }
    Ok(())
}

// ---------------------------------------------------------------------------
// SCVal formatting
// ---------------------------------------------------------------------------

fn escape_str(s: &str, out: &mut String) {
    // Escape `\` first, then `"`, so an embedded quote cannot close the
    // surrounding string delimiters -- otherwise a string could forge extra
    // vec/map items.
    for c in s.chars() {
        if c == '\\' || c == '"' {
            out.push('\\');
        }
        out.push(c);
    }
}

fn require<'a, T>(value: &'a Option<T>, msg: &'static str) -> Result<&'a T> {
    value.as_ref().ok_or(Error::DataError(msg))
}

/// Formats an SCVal as a human-readable string, using JSON for complex types.
pub fn format_sc_val(val: &ScVal) -> Result<String> {
    let mut w = String::new();
    format_sc_val_rec(val, &mut w)?;
    Ok(w)
}

fn format_sc_val_rec(val: &ScVal, w: &mut String) -> Result<()> {
    let ty = sc_type(val).ok_or(Error::DataError("Stellar: unsupported SCVal type"))?;

    match ty {
        ScValType::ScvBool => w.push_str(if *require(&val.b, "Stellar: missing bool value")? {
            "true"
        } else {
            "false"
        }),
        ScValType::ScvVoid => w.push_str("void"),
        ScValType::ScvU32 => {
            w.push_str(&require(&val.u32, "Stellar: missing u32 value")?.to_string())
        }
        ScValType::ScvI32 => {
            w.push_str(&require(&val.i32, "Stellar: missing i32 value")?.to_string())
        }
        ScValType::ScvU64 => {
            w.push_str(&require(&val.u64, "Stellar: missing u64 value")?.to_string())
        }
        ScValType::ScvI64 => {
            w.push_str(&require(&val.i64, "Stellar: missing i64 value")?.to_string())
        }
        ScValType::ScvTimepoint => {
            let timepoint = *require(&val.timepoint, "Stellar: missing timepoint value")?;
            w.push_str(&format_timestamp(timepoint).unwrap_or_else(|| timepoint.to_string()));
        }
        ScValType::ScvDuration => {
            let duration = *require(&val.duration, "Stellar: missing duration value")?;
            w.push_str(&format_duration(duration));
        }
        ScValType::ScvU128 => w.push_str(&format_u128(require(
            &val.u128,
            "Stellar: missing u128 value",
        )?)),
        ScValType::ScvI128 => {
            w.push_str(&i128_value(require(&val.i128, "Stellar: missing i128 value")?).to_string())
        }
        ScValType::ScvU256 => w.push_str(&format_u256(require(
            &val.u256,
            "Stellar: missing u256 value",
        )?)),
        ScValType::ScvI256 => w.push_str(&format_i256(require(
            &val.i256,
            "Stellar: missing i256 value",
        )?)),
        ScValType::ScvBytes => {
            let bytes = require(&val.bytes, "Stellar: missing bytes value")?;
            w.push_str("0x");
            w.push_str(&hex(bytes)?);
        }
        ScValType::ScvString => {
            let bytes = require(&val.string, "Stellar: missing string value")?;
            // Render decoded text as a quoted, escaped string so its content
            // can never forge the surrounding quotes (and thus the vec/map
            // separators). Non-UTF-8 bytes can't be shown as text, so render
            // them as hex like SCV_BYTES.
            match core::str::from_utf8(bytes) {
                Ok(text) => {
                    w.push('"');
                    escape_str(text, w);
                    w.push('"');
                }
                Err(_) => {
                    w.push_str("0x");
                    w.push_str(&hex(bytes)?);
                }
            }
        }
        ScValType::ScvSymbol => {
            // Quote and escape like SCV_STRING so the symbol's content can
            // never forge the surrounding vec/map delimiters. A symbol is
            // already a valid UTF-8 str, so no hex fallback is needed.
            let symbol = require(&val.symbol, "Stellar: missing symbol value")?;
            w.push('"');
            escape_str(symbol, w);
            w.push('"');
        }
        ScValType::ScvVec => format_vec_as_json(&val.vec, w)?,
        ScValType::ScvMap => format_map_as_json(&val.map, w)?,
        ScValType::ScvAddress => {
            w.push_str(require(&val.address, "Stellar: missing address value")?)
        }
    }
    Ok(())
}

fn hex(bytes: &[u8]) -> Result<String> {
    hex_encode(bytes).map_err(|_| Error::DataError("Stellar: invalid bytes value"))
}

/// Formats a vector as a JSON array.
fn format_vec_as_json(vec: &[ScVal], w: &mut String) -> Result<()> {
    w.push('[');
    for (i, item) in vec.iter().enumerate() {
        if i > 0 {
            w.push_str(", ");
        }
        format_sc_val_rec(item, w)?;
    }
    w.push(']');
    Ok(())
}

/// Formats a map as a JSON object.
fn format_map_as_json(map_entries: &[ScValMapEntry], w: &mut String) -> Result<()> {
    w.push('{');
    for (i, entry) in map_entries.iter().enumerate() {
        if i > 0 {
            w.push_str(", ");
        }
        format_sc_val_rec(&entry.key, w)?;
        w.push_str(": ");
        format_sc_val_rec(&entry.value, w)?;
    }
    w.push('}');
    Ok(())
}

fn format_u128(parts: &UInt128Parts) -> String {
    (((parts.hi as u128) << 64) | parts.lo as u128).to_string()
}

fn i128_value(parts: &Int128Parts) -> i128 {
    ((parts.hi as i128) << 64) | parts.lo as i128
}

fn format_u256(parts: &UInt256Parts) -> String {
    U256([parts.lo_lo, parts.lo_hi, parts.hi_lo, parts.hi_hi]).to_string()
}

fn format_i256(parts: &Int256Parts) -> String {
    let value = U256([parts.lo_lo, parts.lo_hi, parts.hi_lo, parts.hi_hi as u64]);
    if parts.hi_hi < 0 {
        // two's complement magnitude
        let magnitude = (!value).overflowing_add(U256::one()).0;
        uformat!("-{}", magnitude.to_string().as_str())
    } else {
        value.to_string()
    }
}

/// Whether the asset is a non-native one, i.e. has an issuer to confirm.
pub(crate) fn asset_has_issuer(asset: &Asset) -> bool {
    asset.r#type != crate::proto::stellar::AssetType::Native as i32
}

/// Shows a paginated text screen asking whether the user wants to see more.
pub(crate) fn should_show_more(title: &str, text: &str, button_text: &str) -> Result<bool> {
    let para = [StrExt::plain(text)];
    ui::should_show_more(
        title,
        &para,
        button_text,
        Some("should_show_more"),
        br(ButtonRequestType::Other),
        tr!("buttons__continue"),
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    fn val(ty: ScValType) -> ScVal {
        ScVal {
            r#type: ty as i32,
            b: None,
            u32: None,
            i32: None,
            u64: None,
            i64: None,
            timepoint: None,
            duration: None,
            u128: None,
            i128: None,
            u256: None,
            i256: None,
            bytes: None,
            string: None,
            symbol: None,
            vec: Vec::new(),
            map: Vec::new(),
            address: None,
        }
    }

    #[test]
    fn scalar_formatting() {
        let mut v = val(ScValType::ScvBool);
        v.b = Some(true);
        assert_eq!(format_sc_val(&v).unwrap(), "true");
        assert_eq!(format_sc_val(&val(ScValType::ScvVoid)).unwrap(), "void");
        let mut v = val(ScValType::ScvI32);
        v.i32 = Some(-5);
        assert_eq!(format_sc_val(&v).unwrap(), "-5");
    }

    #[test]
    fn strings_are_quoted_and_escaped() {
        let mut v = val(ScValType::ScvString);
        v.string = Some(b"a\"b\\c".to_vec());
        assert_eq!(format_sc_val(&v).unwrap(), "\"a\\\"b\\\\c\"");
        // invalid UTF-8 falls back to hex
        v.string = Some(vec![0xff, 0xfe]);
        assert_eq!(format_sc_val(&v).unwrap(), "0xfffe");
    }

    #[test]
    fn nested_vec_and_map() {
        let mut item = val(ScValType::ScvU32);
        item.u32 = Some(7);
        let mut v = val(ScValType::ScvVec);
        v.vec = vec![item.clone(), item.clone()];
        assert_eq!(format_sc_val(&v).unwrap(), "[7, 7]");

        let mut key = val(ScValType::ScvSymbol);
        key.symbol = Some(String::from("k"));
        let mut m = val(ScValType::ScvMap);
        m.map = vec![ScValMapEntry { key, value: item }];
        assert_eq!(format_sc_val(&m).unwrap(), "{\"k\": 7}");
    }

    #[test]
    fn wide_integers() {
        assert_eq!(
            format_u128(&UInt128Parts { hi: 1, lo: 0 }),
            "18446744073709551616"
        );
        assert_eq!(
            i128_value(&Int128Parts {
                hi: -1,
                lo: u64::MAX
            }),
            -1
        );
        assert_eq!(
            format_i256(&Int256Parts {
                hi_hi: -1,
                hi_lo: u64::MAX,
                lo_hi: u64::MAX,
                lo_lo: u64::MAX
            }),
            "-1"
        );
        assert_eq!(
            format_u256(&UInt256Parts {
                hi_hi: 0,
                hi_lo: 0,
                lo_hi: 1,
                lo_lo: 0
            }),
            "18446744073709551616"
        );
    }

    #[test]
    fn sep41_amounts_must_be_non_negative_i128() {
        let mut v = val(ScValType::ScvI128);
        v.i128 = Some(Int128Parts { hi: 0, lo: 42 });
        assert_eq!(sc_amount(&v), Some(42));
        v.i128 = Some(Int128Parts {
            hi: -1,
            lo: u64::MAX,
        });
        assert_eq!(sc_amount(&v), None);
    }
}

use crate::{
    alloc_types::Vec,
    common::get_encoded_address,
    helpers::{
        chunkify_number, format_blocks_as_time, format_energy_amount, format_token_amount,
        format_trx_amount,
    },
    proto::tron::{ResourceCode, TransferContract, TriggerSmartContract},
    uformat,
};
use primitive_types::U256;
use trezor_app_sdk::{
    Result, ResultExt,
    modui::{self, Field},
};

/// The facts behind the "Account info" extra: the account's name when it has one,
/// and its derivation path.
fn account_facts<'a>(name: Option<&'a str>, path: Option<&'a str>) -> Vec<Field<'a>> {
    let mut facts = Vec::with_capacity(2);
    if let Some(name) = name {
        facts.push(Field::text(tr!("words__account"), name));
    }
    if let Some(path) = path {
        facts.push(Field::text(tr!("address_details__derivation_path"), path));
    }
    facts
}

/// Offers the "Account info" extra, unless there is nothing to show in it.
fn with_account_info<'a>(review: modui::Review<'a>, facts: &'a [Field<'a>]) -> modui::Review<'a> {
    if facts.is_empty() {
        review
    } else {
        review.extra(tr!("address_details__account_info"), facts)
    }
}

/// A note attached to a transaction: free-form text supplied by the sender.
pub fn confirm_note(note: &str) -> Result<()> {
    let facts = [Field::note(note)];
    modui::review("note", tr!("words__note"), &facts)
        .confirm()
        .c()
}

pub fn confirm_freeze_operations(
    owner_address: &[u8],
    balance: u64,
    resource: i32,
    title: &str,
) -> Result<()> {
    let address = get_encoded_address(owner_address).c()?;
    let owner = [Field::address(tr!("tron__owner_address"), &address)];
    modui::review("freeze/owner", title, &owner).confirm().c()?;

    let amount = format_trx_amount(balance);
    let summary = [
        Field::amount(tr!("words__amount"), &amount),
        Field::text(tr!("words__resource"), resource_name(resource)),
    ];
    modui::review("freeze", tr!("words__title_summary"), &summary)
        .confirm_final()
        .c()
}

fn resource_name(resource: i32) -> &'static str {
    if resource == ResourceCode::Energy as i32 {
        "Energy"
    } else {
        "Bandwidth"
    }
}

pub fn confirm_delegate_resource(
    receiver_address: &[u8],
    balance: u64,
    resource: i32,
    lock_period: Option<u64>,
) -> Result<()> {
    let title = tr!("tron__delegate_resource");
    let address = get_encoded_address(receiver_address).c()?;

    let recipient = [Field::address(tr!("words__recipient"), &address)];
    modui::review("delegate/recipient", title, &recipient)
        .confirm()
        .c()?;

    let amount = format_trx_amount(balance);
    let summary = [
        Field::amount(tr!("words__amount"), &amount),
        Field::text(tr!("words__resource"), resource_name(resource)),
    ];
    let review = modui::review("delegate/resource", title, &summary);
    if lock_period.is_none() {
        review.confirm_final().c()?;
    } else {
        review.confirm().c()?;
    }

    if let Some(lock_period) = lock_period {
        let time = format_blocks_as_time(lock_period);
        let blocks = chunkify_number(lock_period);
        let lock = [
            Field::text(tr!("tron__lockperiod_time"), &time),
            Field::text(tr!("tron__lockperiod_blocks"), &blocks),
        ];
        modui::review("delegate/lock_period", tr!("tron__lock_period"), &lock)
            .confirm_final()
            .c()?;
    }

    Ok(())
}

pub fn confirm_undelegate_resource(
    receiver_address: &[u8],
    balance: u64,
    resource: i32,
) -> Result<()> {
    let title = tr!("tron__undelegate_resource");
    let address = get_encoded_address(receiver_address).c()?;

    let receiver = [Field::address(tr!("words__from_title"), &address)];
    modui::review("undelegate/from_address", title, &receiver)
        .confirm()
        .c()?;

    let amount = format_trx_amount(balance);
    let summary = [
        Field::amount(tr!("words__amount"), &amount),
        Field::text(tr!("words__resource"), resource_name(resource)),
    ];
    modui::review("undelegate/resource", title, &summary)
        .confirm_final()
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
        let owner = [
            Field::address(tr!("tron__owner_address"), owner_address),
            Field::warning(tr!("address__warning_not_yours")),
        ];
        modui::review("claim/owner", title, &owner).confirm().c()?;
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
    let account = account_facts(account, account_path);
    let question = [Field::note(intro_question)];

    with_account_info(modui::review("claim", title, &question), &account)
        .confirm_final()
        .c()
}

fn confirm_tron_summary(
    title: Option<&str>,
    amount: Option<&str>,
    fee: Option<&str>,
    account_details: Option<(Option<&str>, &str)>,
) -> Result<()> {
    let mut summary = Vec::with_capacity(2);
    if let Some(amount) = amount {
        summary.push(Field::amount(tr!("words__amount"), amount));
    }
    if let Some(fee) = fee {
        summary.push(Field::amount(tr!("words__fee_limit"), fee));
    }

    let account =
        account_details.map_or_else(Vec::new, |(name, path)| account_facts(name, Some(path)));

    with_account_info(
        modui::review("summary", title.unwrap_or(tr!("words__send")), &summary),
        &account,
    )
    .confirm_final()
    .c()
}

fn confirm_tron_send(
    amount: Option<&str>,
    fee: Option<&str>,
    account_details: (Option<&str>, &str),
    address: &str,
) -> Result<()> {
    let account = account_facts(account_details.0, Some(account_details.1));
    let recipient = [Field::address(tr!("words__recipient"), address)];

    with_account_info(
        modui::review("send", tr!("words__send"), &recipient),
        &account,
    )
    .confirm()
    .c()?;

    confirm_tron_summary(Some(tr!("words__send")), amount, fee, Some(account_details))
}

pub fn confirm_tron_transfer(
    recipient_addr: &str,
    amount_str: &str,
    maximum_fee: &str,
    native_amount_str: Option<&str>,
) -> Result<()> {
    let title = tr!("words__send");

    let recipient = [Field::address(tr!("words__recipient"), recipient_addr)];
    modui::review("transfer", title, &recipient).confirm().c()?;

    let amount = [
        Field::amount(tr!("words__amount"), amount_str),
        Field::text(tr!("words__chain"), "Tron"),
    ];
    modui::review("transfer/amount", title, &amount)
        .confirm()
        .c()?;

    let mut summary = Vec::with_capacity(2);
    if let Some(native_amount) = native_amount_str {
        summary.push(Field::amount(tr!("words__amount"), native_amount));
    }
    summary.push(Field::amount(tr!("words__fee_limit"), maximum_fee));
    modui::review("transfer/summary", title, &summary)
        .confirm_final()
        .c()
}

fn confirm_tron_approve(
    recipient_addr: &str,
    amount_str: &str,
    is_revoke: bool,
    maximum_fee: &str,
    native_amount_str: Option<&str>,
) -> Result<()> {
    let (title, action_subtitle, value_subtitle, allowance) = if is_revoke {
        (
            tr!("ethereum__approve_intro_title_revoke"),
            tr!("ethereum__approve_intro_revoke"),
            tr!("ethereum__approve_revoke_from"),
            Field::amount(tr!("words__token"), &amount_str[2..]),
        )
    } else {
        (
            tr!("ethereum__approve_intro_title"),
            tr!("ethereum__approve_intro"),
            tr!("ethereum__approve_to"),
            Field::amount(tr!("ethereum__approve_amount_allowance"), amount_str),
        )
    };

    let intro = [Field::note(action_subtitle)];
    modui::review("approve", title, &intro).confirm().c()?;

    let spender = [Field::address(value_subtitle, recipient_addr)];
    modui::review("approve/spender", title, &spender)
        .confirm()
        .c()?;

    let amount = [allowance, Field::text(tr!("words__chain"), "Tron")];
    modui::review("approve/amount", title, &amount)
        .confirm()
        .c()?;

    let mut summary = Vec::with_capacity(2);
    if let Some(native_amount) = native_amount_str {
        summary.push(Field::amount(tr!("words__amount"), native_amount));
    }
    summary.push(Field::amount(tr!("words__fee_limit"), maximum_fee));
    modui::review("approve/summary", title, &summary)
        .confirm_final()
        .c()
}

pub fn confirm_tron_voting<'a>(items: &'a [Field<'a>]) -> Result<()> {
    modui::review("vote", tr!("words__voting"), items)
        .confirm_final()
        .c()
}

fn confirm_ethereum_unknown_contract_warning() -> Result<()> {
    let content = uformat!(
        "{} {}",
        tr!("ethereum__unknown_contract_address"),
        tr!("words__know_what_your_doing")
    );

    let warning = [Field::note(&content)];
    modui::danger("unknown_contract", tr!("words__important"), &warning).c()
}

pub fn confirm_unknown_smart_contract(
    contract: &TriggerSmartContract,
    fee_limit: u64,
    trx_value: Option<u64>,
) -> Result<()> {
    confirm_ethereum_unknown_contract_warning().c()?;

    let contract_address = get_encoded_address(&contract.contract_address).c()?;
    let address = [Field::address(tr!("words__address"), &contract_address)];
    modui::review("contract", tr!("ethereum__token_contract"), &address)
        .confirm()
        .c()?;

    // The app hands over the raw calldata and gets one outcome; the hex, how it
    // is split up, and the button labels are not the app's.
    let data = [Field::data(
        tr!("ethereum__title_input_data"),
        &contract.data,
    )];
    modui::review("contract/data", tr!("ethereum__title_input_data"), &data)
        .confirm()
        .c()?;

    let amount = trx_value.map(format_trx_amount);
    let fee = format_energy_amount(fee_limit);
    confirm_tron_summary(
        Some(tr!("words__title_summary")),
        amount.as_deref(),
        Some(&fee),
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
    trx_value: Option<u64>,
) -> Result<()> {
    let native_amount_str = trx_value.map(format_trx_amount);
    let native_amount_str = native_amount_str.as_deref();

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
            native_amount_str,
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
            native_amount_str,
        )
        .c()?;
    }

    Ok(())
}

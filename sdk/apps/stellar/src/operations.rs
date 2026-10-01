//! Operation handling: decoding, confirmation on the display and XDR
//! serialization. Ported from Core's `apps/stellar/operations/`.

use crate::{
    alloc_types::{String, ToString, Vec},
    consts::{
        FLAG_AUTH_IMMUTABLE, FLAG_AUTH_REQUIRED, FLAG_AUTH_REVOCABLE, FLAGS_MAX_SIZE, op_code,
    },
    helpers::{address_from_public_key, sha256},
    layout::{
        asset_has_issuer, confirm_address, confirm_create_contract, confirm_invocation,
        confirm_invoke_contract, confirm_plain_value, confirm_properties, confirm_stellar_output,
        confirm_stellar_output_amount, fill, should_show_more,
    },
    payment_request::PaymentRequestVerifier,
    proto::{
        common::button_request::ButtonRequestType,
        messages::MessageType,
        stellar::{
            AccountMergeOp, AllowTrustOp, Asset, BumpSequenceOp, ChangeTrustOp,
            ClaimClaimableBalanceOp, CreateAccountOp, CreatePassiveSellOfferOp, HostFunction,
            InvokeHostFunctionOp, ManageBuyOfferOp, ManageDataOp, ManageSellOfferOp,
            PathPaymentStrictReceiveOp, PathPaymentStrictSendOp, PaymentOp, SetOptionsOp,
            SorobanAuthorizationEntry, host_function::HostFunctionType, set_options_op::SignerType,
            soroban_authorized_function::SorobanAuthorizedFunctionType,
            soroban_credentials::SorobanCredentialsType,
        },
    },
    serialize,
    strutil::hex_encode,
    tokens::StellarToken,
    uformat,
    writers::{Writer, write_create_contract_args_v2, write_invoke_contract_args, write_uint32},
};
use core::fmt::Write as _;
use prost::Message;
use trezor_app_sdk::{Error, Result, ResultExt, ui::Property};

/// An operation of the transaction being signed, as sent by the host.
pub enum Operation {
    AccountMerge(AccountMergeOp),
    AllowTrust(AllowTrustOp),
    BumpSequence(BumpSequenceOp),
    ChangeTrust(ChangeTrustOp),
    CreateAccount(CreateAccountOp),
    CreatePassiveSellOffer(CreatePassiveSellOfferOp),
    ManageData(ManageDataOp),
    ManageBuyOffer(ManageBuyOfferOp),
    ManageSellOffer(ManageSellOfferOp),
    PathPaymentStrictReceive(PathPaymentStrictReceiveOp),
    PathPaymentStrictSend(PathPaymentStrictSendOp),
    Payment(PaymentOp),
    SetOptions(SetOptionsOp),
    ClaimClaimableBalance(ClaimClaimableBalanceOp),
    InvokeHostFunction(InvokeHostFunctionOp),
}

fn decode<M: Message + Default>(data: &[u8]) -> Result<M> {
    M::decode(data).map_err(|_| Error::InvalidMessage)
}

impl Operation {
    /// The message types the device accepts as a response to `TxOpRequest`.
    pub fn decode(id: MessageType, data: &[u8]) -> Result<Self> {
        Ok(match id {
            MessageType::AccountMergeOp => Self::AccountMerge(decode(data)?),
            MessageType::AllowTrustOp => Self::AllowTrust(decode(data)?),
            MessageType::BumpSequenceOp => Self::BumpSequence(decode(data)?),
            MessageType::ChangeTrustOp => Self::ChangeTrust(decode(data)?),
            MessageType::CreateAccountOp => Self::CreateAccount(decode(data)?),
            MessageType::CreatePassiveSellOfferOp => Self::CreatePassiveSellOffer(decode(data)?),
            MessageType::ManageDataOp => Self::ManageData(decode(data)?),
            MessageType::ManageBuyOfferOp => Self::ManageBuyOffer(decode(data)?),
            MessageType::ManageSellOfferOp => Self::ManageSellOffer(decode(data)?),
            MessageType::PathPaymentStrictReceiveOp => {
                Self::PathPaymentStrictReceive(decode(data)?)
            }
            MessageType::PathPaymentStrictSendOp => Self::PathPaymentStrictSend(decode(data)?),
            MessageType::PaymentOp => Self::Payment(decode(data)?),
            MessageType::SetOptionsOp => Self::SetOptions(decode(data)?),
            MessageType::ClaimClaimableBalanceOp => Self::ClaimClaimableBalance(decode(data)?),
            MessageType::InvokeHostFunctionOp => Self::InvokeHostFunction(decode(data)?),
            _ => return Err(Error::InvalidMessage),
        })
    }

    pub fn source_account(&self) -> Option<&str> {
        match self {
            Self::AccountMerge(op) => op.source_account.as_deref(),
            Self::AllowTrust(op) => op.source_account.as_deref(),
            Self::BumpSequence(op) => op.source_account.as_deref(),
            Self::ChangeTrust(op) => op.source_account.as_deref(),
            Self::CreateAccount(op) => op.source_account.as_deref(),
            Self::CreatePassiveSellOffer(op) => op.source_account.as_deref(),
            Self::ManageData(op) => op.source_account.as_deref(),
            Self::ManageBuyOffer(op) => op.source_account.as_deref(),
            Self::ManageSellOffer(op) => op.source_account.as_deref(),
            Self::PathPaymentStrictReceive(op) => op.source_account.as_deref(),
            Self::PathPaymentStrictSend(op) => op.source_account.as_deref(),
            Self::Payment(op) => op.source_account.as_deref(),
            Self::SetOptions(op) => op.source_account.as_deref(),
            Self::ClaimClaimableBalance(op) => op.source_account.as_deref(),
            Self::InvokeHostFunction(op) => op.source_account.as_deref(),
        }
    }

    fn message_type(&self) -> MessageType {
        match self {
            Self::AccountMerge(_) => MessageType::AccountMergeOp,
            Self::AllowTrust(_) => MessageType::AllowTrustOp,
            Self::BumpSequence(_) => MessageType::BumpSequenceOp,
            Self::ChangeTrust(_) => MessageType::ChangeTrustOp,
            Self::CreateAccount(_) => MessageType::CreateAccountOp,
            Self::CreatePassiveSellOffer(_) => MessageType::CreatePassiveSellOfferOp,
            Self::ManageData(_) => MessageType::ManageDataOp,
            Self::ManageBuyOffer(_) => MessageType::ManageBuyOfferOp,
            Self::ManageSellOffer(_) => MessageType::ManageSellOfferOp,
            Self::PathPaymentStrictReceive(_) => MessageType::PathPaymentStrictReceiveOp,
            Self::PathPaymentStrictSend(_) => MessageType::PathPaymentStrictSendOp,
            Self::Payment(_) => MessageType::PaymentOp,
            Self::SetOptions(_) => MessageType::SetOptionsOp,
            Self::ClaimClaimableBalance(_) => MessageType::ClaimClaimableBalanceOp,
            Self::InvokeHostFunction(_) => MessageType::InvokeHostFunctionOp,
        }
    }

    /// Whether the operation sends funds to an output, i.e. counts towards the
    /// recipient numbering shown on the display.
    pub fn is_output(&self) -> bool {
        matches!(
            self,
            Self::AccountMerge(_)
                | Self::CreateAccount(_)
                | Self::Payment(_)
                | Self::PathPaymentStrictSend(_)
                | Self::PathPaymentStrictReceive(_)
        )
    }
}

/// Confirms `op` on the display and appends its XDR to `w`.
pub fn process_operation(
    w: &mut dyn Writer,
    op: &Operation,
    output_index: usize,
    payment_request_verifier: Option<&mut PaymentRequestVerifier>,
    tx_source_account: &str,
    network_id: &[u8; 32],
) -> Result<()> {
    if let Some(source_account) = op.source_account().filter(|s| !s.is_empty()) {
        confirm_source_account(source_account).c()?;
    }
    serialize::write_account(w, op.source_account()).c()?;
    write_uint32(
        w,
        op_code(op.message_type()).ok_or(Error::DataError("Stellar: op code unknown"))?,
    );

    if let Some(verifier) = payment_request_verifier {
        return match op {
            Operation::Payment(op) => {
                // will be confirmed as part of payment request confirmation
                serialize::write_payment_op(w, op).c()?;
                verifier
                    .add_output(
                        u64::try_from(op.amount)
                            .map_err(|_| Error::DataError("Stellar: negative amount"))?,
                        &op.destination_account,
                    )
                    .c()
            }
            _ => Err(Error::DataError("Invalid operation for payment request")),
        };
    }

    match op {
        Operation::AccountMerge(op) => {
            confirm_account_merge_op(op, output_index).c()?;
            serialize::write_account_merge_op(w, op).c()
        }
        Operation::AllowTrust(op) => {
            confirm_allow_trust_op(op).c()?;
            serialize::write_allow_trust_op(w, op).c()
        }
        Operation::BumpSequence(op) => {
            confirm_bump_sequence_op(op).c()?;
            serialize::write_bump_sequence_op(w, op);
            Ok(())
        }
        Operation::ChangeTrust(op) => {
            confirm_change_trust_op(op).c()?;
            serialize::write_change_trust_op(w, op).c()
        }
        Operation::CreateAccount(op) => {
            confirm_create_account_op(op, output_index).c()?;
            serialize::write_create_account_op(w, op).c()
        }
        Operation::CreatePassiveSellOffer(op) => {
            confirm_create_passive_sell_offer_op(op).c()?;
            serialize::write_create_passive_sell_offer_op(w, op).c()
        }
        Operation::ManageData(op) => {
            confirm_manage_data_op(op).c()?;
            serialize::write_manage_data_op(w, op).c()
        }
        Operation::ManageBuyOffer(op) => {
            confirm_manage_buy_offer_op(op).c()?;
            serialize::write_manage_buy_offer_op(w, op).c()
        }
        Operation::ManageSellOffer(op) => {
            confirm_manage_sell_offer_op(op).c()?;
            serialize::write_manage_sell_offer_op(w, op).c()
        }
        Operation::PathPaymentStrictReceive(op) => {
            confirm_path_payment_strict_receive_op(op, output_index).c()?;
            serialize::write_path_payment_strict_receive_op(w, op).c()
        }
        Operation::PathPaymentStrictSend(op) => {
            confirm_path_payment_strict_send_op(op, output_index).c()?;
            serialize::write_path_payment_strict_send_op(w, op).c()
        }
        Operation::Payment(op) => {
            confirm_payment_op(op, output_index).c()?;
            serialize::write_payment_op(w, op).c()
        }
        Operation::SetOptions(op) => {
            confirm_set_options_op(op).c()?;
            serialize::write_set_options_op(w, op).c()
        }
        Operation::ClaimClaimableBalance(op) => {
            confirm_claim_claimable_balance_op(op).c()?;
            serialize::write_claim_claimable_balance_op(w, op).c()
        }
        Operation::InvokeHostFunction(op) => {
            confirm_invoke_host_function_op(op, tx_source_account, network_id).c()?;
            serialize::write_invoke_host_function_op(w, op).c()
        }
    }
}

// ---------------------------------------------------------------------------
// Confirmations
// ---------------------------------------------------------------------------

fn amount(value: i64) -> Result<u128> {
    u128::try_from(value).map_err(|_| Error::DataError("Stellar: negative amount"))
}

fn confirm_source_account(source_account: &str) -> Result<()> {
    confirm_address(
        tr!("stellar__confirm_operation"),
        source_account,
        Some(tr!("stellar__source_account")),
        "op_source_account",
        true,
    )
}

fn confirm_allow_trust_op(op: &AllowTrustOp) -> Result<()> {
    confirm_properties(
        "op_allow_trust",
        if op.is_authorized {
            tr!("stellar__allow_trust")
        } else {
            tr!("stellar__revoke_trust")
        },
        &[
            Property::mono(tr!("words__asset"), op.asset_code.as_deref().unwrap_or("")),
            Property::mono(tr!("stellar__trusted_account"), &op.trusted_account),
        ],
        None,
        Some(tr!("buttons__continue")),
    )
}

fn confirm_account_merge_op(op: &AccountMergeOp, output_index: usize) -> Result<()> {
    crate::layout::confirm_address_full(
        tr!("stellar__account_merge"),
        &op.destination_account,
        Some(&uformat!(
            "{} #{}",
            tr!("words__recipient"),
            output_index + 1
        )),
        Some(tr!("stellar__all_will_be_sent_to")),
        Some(tr!("buttons__continue")),
        "op_account_merge",
        ButtonRequestType::Other as i32,
        None,
        None,
    )
}

fn confirm_bump_sequence_op(op: &BumpSequenceOp) -> Result<()> {
    confirm_plain_value(
        tr!("stellar__bump_sequence"),
        &fill(
            tr!("stellar__set_sequence_to_template"),
            &op.bump_to.to_string(),
        ),
        Some(""),
        "op_bump",
    )
}

fn confirm_change_trust_op(op: &ChangeTrustOp) -> Result<()> {
    confirm_plain_value(
        if op.limit == 0 {
            tr!("stellar__delete_trust")
        } else {
            tr!("stellar__add_trust")
        },
        &StellarToken::from_asset(&op.asset)
            .c()?
            .format(op.limit as u128),
        Some(tr!("stellar__limit")),
        "op_change_trust",
    )
    .c()?;

    confirm_asset_issuer(&op.asset)
}

fn confirm_create_account_op(op: &CreateAccountOp, output_index: usize) -> Result<()> {
    let token = StellarToken::native();
    confirm_stellar_output(
        &op.new_account,
        &token.format(amount(op.starting_balance).c()?),
        output_index,
        &token,
        None,
        None,
        None,
    )
}

fn confirm_create_passive_sell_offer_op(op: &CreatePassiveSellOfferOp) -> Result<()> {
    let title = if op.amount == 0 {
        tr!("stellar__delete_passive_offer")
    } else {
        tr!("stellar__new_passive_offer")
    };
    confirm_offer(
        title,
        Offer {
            selling_asset: &op.selling_asset,
            buying_asset: &op.buying_asset,
            amount: op.amount,
            price_n: op.price_n,
            price_d: op.price_d,
            is_buy: false,
        },
    )
}

fn confirm_manage_buy_offer_op(op: &ManageBuyOfferOp) -> Result<()> {
    confirm_manage_offer_op_common(
        op.offer_id,
        Offer {
            selling_asset: &op.selling_asset,
            buying_asset: &op.buying_asset,
            amount: op.amount,
            price_n: op.price_n,
            price_d: op.price_d,
            is_buy: true,
        },
    )
}

fn confirm_manage_sell_offer_op(op: &ManageSellOfferOp) -> Result<()> {
    confirm_manage_offer_op_common(
        op.offer_id,
        Offer {
            selling_asset: &op.selling_asset,
            buying_asset: &op.buying_asset,
            amount: op.amount,
            price_n: op.price_n,
            price_d: op.price_d,
            is_buy: false,
        },
    )
}

fn confirm_manage_offer_op_common(offer_id: u64, offer: Offer) -> Result<()> {
    let text = if offer_id == 0 {
        String::from(tr!("stellar__new_offer"))
    } else {
        uformat!(
            "{} #{}",
            if offer.amount == 0 {
                tr!("stellar__delete")
            } else {
                tr!("stellar__update")
            },
            offer_id
        )
    };
    confirm_offer(&text, offer)
}

struct Offer<'a> {
    selling_asset: &'a Asset,
    buying_asset: &'a Asset,
    amount: i64,
    price_n: u32,
    price_d: u32,
    /// A buy offer's `amount` is the amount being bought, otherwise sold.
    is_buy: bool,
}

/// Formats `n / d` the way Core prints the float division, which is
/// single-precision in Core's MicroPython, i.e. `%.7g` plus a `.0` for
/// integral values.
fn format_price(n: u32, d: u32) -> String {
    let value = (n as f32 / d as f32) as f64;
    if value == 0.0 {
        return String::from("0.0");
    }

    // `%.7g`: 7 significant digits, scientific notation for exponents < -4 or >= 7.
    let mut scientific = String::new();
    let _ = write!(scientific, "{:.6e}", value);
    let (mantissa, exponent) = scientific.split_once('e').unwrap_or((&scientific, "0"));
    let exponent: i32 = exponent.parse().unwrap_or(0);
    let digits: String = mantissa.chars().filter(|c| c.is_ascii_digit()).collect();

    let mut out = String::new();
    if !(-4..7).contains(&exponent) {
        let trimmed = digits.trim_end_matches('0');
        out.push_str(&trimmed[..1]);
        if trimmed.len() > 1 {
            out.push('.');
            out.push_str(&trimmed[1..]);
        }
        let _ = write!(
            out,
            "e{}{:02}",
            if exponent < 0 { '-' } else { '+' },
            exponent.unsigned_abs()
        );
        return out;
    }

    if exponent < 0 {
        out.push_str("0.");
        for _ in 0..(-exponent - 1) {
            out.push('0');
        }
        out.push_str(digits.trim_end_matches('0'));
    } else {
        let int_len = exponent as usize + 1;
        out.push_str(&digits[..int_len]);
        let frac = digits[int_len..].trim_end_matches('0');
        out.push('.');
        out.push_str(if frac.is_empty() { "0" } else { frac });
    }
    out
}

fn confirm_offer(title: &str, offer: Offer) -> Result<()> {
    if offer.price_d == 0 {
        return Err(Error::DataError("Stellar: invalid price denominator"));
    }

    let buying_token = StellarToken::from_asset(offer.buying_asset).c()?;
    let selling_token = StellarToken::from_asset(offer.selling_asset).c()?;
    let amount = amount(offer.amount).c()?;

    let (first_label, first, second_label, second, price_symbol) = if offer.is_buy {
        (
            tr!("stellar__buying"),
            buying_token.format(amount),
            tr!("stellar__selling"),
            selling_token.symbol.clone(),
            &selling_token.symbol,
        )
    } else {
        (
            tr!("stellar__selling"),
            selling_token.format(amount),
            tr!("stellar__buying"),
            buying_token.symbol.clone(),
            &buying_token.symbol,
        )
    };
    let price_label = fill(tr!("stellar__price_per_template"), price_symbol);
    let price = format_price(offer.price_n, offer.price_d);

    confirm_properties(
        "op_offer",
        title,
        &[
            Property::plain(first_label, &first),
            Property::plain(second_label, &second),
            Property::plain(&price_label, &price),
        ],
        None,
        Some(tr!("buttons__continue")),
    )
    .c()?;

    confirm_asset_issuer(offer.selling_asset).c()?;
    confirm_asset_issuer(offer.buying_asset)
}

fn confirm_manage_data_op(op: &ManageDataOp) -> Result<()> {
    match op.value.as_deref().filter(|v| !v.is_empty()) {
        Some(value) => {
            let digest = hex_encode(&sha256(value))
                .map_err(|_| Error::DataError("Stellar: invalid value"))?;
            confirm_properties(
                "op_data",
                tr!("stellar__set_data"),
                &[
                    Property::mono(tr!("stellar__key"), &op.key),
                    Property::mono(tr!("stellar__value_sha256"), &digest),
                ],
                None,
                Some(tr!("buttons__continue")),
            )
        }
        None => confirm_plain_value(
            tr!("stellar__clear_data"),
            &fill(tr!("stellar__wanna_clean_value_key_template"), &op.key),
            Some(""),
            "op_data",
        ),
    }
}

fn confirm_path_payment_strict_receive_op(
    op: &PathPaymentStrictReceiveOp,
    output_index: usize,
) -> Result<()> {
    let destination_token = StellarToken::from_asset(&op.destination_asset).c()?;
    let send_token = StellarToken::from_asset(&op.send_asset).c()?;
    confirm_stellar_output(
        &op.destination_account,
        &destination_token.format(amount(op.destination_amount).c()?),
        output_index,
        &destination_token,
        Some(tr!("stellar__path_pay")),
        Some(tr!("stellar__path_pay")),
        None,
    )
    .c()?;

    confirm_stellar_output_amount(
        tr!("stellar__debited_amount"),
        &uformat!("{} #{}", tr!("words__recipient"), output_index + 1),
        &send_token.format(amount(op.send_max).c()?),
        &send_token,
        Some(tr!("stellar__pay_at_most")),
        None,
    )
}

fn confirm_path_payment_strict_send_op(
    op: &PathPaymentStrictSendOp,
    output_index: usize,
) -> Result<()> {
    let destination_token = StellarToken::from_asset(&op.destination_asset).c()?;
    let send_token = StellarToken::from_asset(&op.send_asset).c()?;
    confirm_stellar_output(
        &op.destination_account,
        &destination_token.format(amount(op.destination_min).c()?),
        output_index,
        &destination_token,
        Some(tr!("stellar__path_pay_at_least")),
        Some(tr!("stellar__path_pay_at_least")),
        None,
    )
    .c()?;

    confirm_stellar_output_amount(
        tr!("stellar__debited_amount"),
        &uformat!("{} #{}", tr!("words__recipient"), output_index + 1),
        &send_token.format(amount(op.send_amount).c()?),
        &send_token,
        Some(tr!("stellar__pay")),
        None,
    )
}

fn confirm_payment_op(op: &PaymentOp, output_index: usize) -> Result<()> {
    let token = StellarToken::from_asset(&op.asset).c()?;
    confirm_stellar_output(
        &op.destination_account,
        &token.format(amount(op.amount).c()?),
        output_index,
        &token,
        None,
        None,
        None,
    )
}

fn confirm_set_options_op(op: &SetOptionsOp) -> Result<()> {
    if let Some(inflation) = op
        .inflation_destination_account
        .as_deref()
        .filter(|s| !s.is_empty())
    {
        confirm_address_labeled(
            tr!("stellar__inflation"),
            inflation,
            tr!("stellar__destination"),
            "op_inflation",
        )
        .c()?;
    }

    if let Some(flags) = op.clear_flags.filter(|f| *f != 0) {
        confirm_plain_value(
            tr!("stellar__clear_flags"),
            &format_flags(flags).c()?,
            Some(""),
            "op_clear_flags",
        )
        .c()?;
    }

    if let Some(flags) = op.set_flags.filter(|f| *f != 0) {
        confirm_plain_value(
            tr!("stellar__set_flags"),
            &format_flags(flags).c()?,
            Some(""),
            "op_set_flags",
        )
        .c()?;
    }

    let thresholds = [
        (tr!("stellar__master_weight"), op.master_weight),
        (tr!("stellar__low"), op.low_threshold),
        (tr!("stellar__medium"), op.medium_threshold),
        (tr!("stellar__high"), op.high_threshold),
    ];
    let values: Vec<(&str, String)> = thresholds
        .iter()
        .filter_map(|(label, value)| value.map(|v| (*label, v.to_string())))
        .collect();
    if !values.is_empty() {
        let props: Vec<Property> = values
            .iter()
            .map(|(label, value)| Property::mono(label, value))
            .collect();
        confirm_properties(
            "op_thresholds",
            tr!("stellar__account_thresholds"),
            &props,
            None,
            Some(tr!("buttons__continue")),
        )
        .c()?;
    }

    if let Some(home_domain) = op.home_domain.as_deref().filter(|s| !s.is_empty()) {
        confirm_plain_value(
            tr!("stellar__home_domain"),
            home_domain,
            Some(""),
            "op_home_domain",
        )
        .c()?;
    }

    if let Some(signer_type) = op.signer_type {
        let (Some(signer_key), Some(signer_weight)) = (&op.signer_key, op.signer_weight) else {
            return Err(Error::DataError("Stellar: invalid signer option data."));
        };

        let (description, data) = match SignerType::try_from(signer_type) {
            Ok(SignerType::Account) => (tr!("words__account"), address_from_public_key(signer_key)),
            Ok(SignerType::PreAuth) => (
                tr!("stellar__preauth_transaction"),
                hex_encode(signer_key).map_err(|_| Error::DataError("Stellar: invalid signer"))?,
            ),
            Ok(SignerType::Hash) => (
                tr!("stellar__hash"),
                hex_encode(signer_key).map_err(|_| Error::DataError("Stellar: invalid signer"))?,
            ),
            Err(_) => return Err(Error::DataError("Stellar: invalid signer type")),
        };

        let weight = signer_weight.to_string();
        let mut props = Vec::with_capacity(2);
        props.push(Property::mono(description, &data));
        let title = if signer_weight > 0 {
            props.push(Property::mono(tr!("words__weight"), &weight));
            tr!("stellar__add_signer")
        } else {
            tr!("stellar__remove_signer")
        };

        confirm_properties(
            "op_signer",
            title,
            &props,
            None,
            Some(tr!("buttons__continue")),
        )
        .c()?;
    }
    Ok(())
}

fn confirm_claim_claimable_balance_op(op: &ClaimClaimableBalanceOp) -> Result<()> {
    let balance_id =
        hex_encode(&op.balance_id).map_err(|_| Error::DataError("Stellar: invalid balance id"))?;
    confirm_properties(
        "op_claim_claimable_balance",
        tr!("stellar__claim_claimable_balance"),
        &[Property::mono(tr!("stellar__balance_id"), &balance_id)],
        None,
        Some(tr!("buttons__continue")),
    )
}

fn format_flags(flags: u32) -> Result<String> {
    if flags > FLAGS_MAX_SIZE {
        return Err(Error::DataError("Stellar: invalid flags"));
    }
    let mut flags_set = String::new();
    if flags & FLAG_AUTH_REQUIRED != 0 {
        flags_set.push_str("AUTH_REQUIRED\n");
    }
    if flags & FLAG_AUTH_REVOCABLE != 0 {
        flags_set.push_str("AUTH_REVOCABLE\n");
    }
    if flags & FLAG_AUTH_IMMUTABLE != 0 {
        flags_set.push_str("AUTH_IMMUTABLE\n");
    }
    Ok(flags_set)
}

fn confirm_address_labeled(
    title: &str,
    address: &str,
    description: &str,
    br_name: &str,
) -> Result<()> {
    confirm_address(title, address, Some(description), br_name, true)
}

fn confirm_asset_issuer(asset: &Asset) -> Result<()> {
    if !asset_has_issuer(asset) {
        return Ok(());
    }
    let (Some(issuer), Some(code)) = (&asset.issuer, &asset.code) else {
        return Err(Error::DataError("Stellar: invalid asset definition"));
    };
    confirm_address(
        tr!("stellar__confirm_issuer"),
        issuer,
        Some(&fill(tr!("stellar__issuer_template"), code)),
        "confirm_asset_issuer",
        true,
    )
}

/// Whether the entry's root invocation is the invoked host function itself.
///
/// Such an entry only authorizes what the user has already confirmed, so its
/// root is not shown again. The two are compared in their XDR form.
fn is_root_auth_entry(auth_entry: &SorobanAuthorizationEntry, invoked_fn: &HostFunction) -> bool {
    let auth_fn = &auth_entry.root_invocation.function;
    let auth_type = SorobanAuthorizedFunctionType::try_from(auth_fn.r#type).ok();
    let invoked_type = HostFunctionType::try_from(invoked_fn.r#type).ok();

    match (auth_type, invoked_type) {
        (
            Some(SorobanAuthorizedFunctionType::ContractFn),
            Some(HostFunctionType::InvokeContract),
        ) => match (&auth_fn.contract_fn, &invoked_fn.invoke_contract) {
            (Some(a), Some(b)) => {
                let (mut xa, mut xb) = (Vec::new(), Vec::new());
                write_invoke_contract_args(&mut xa, a).is_ok()
                    && write_invoke_contract_args(&mut xb, b).is_ok()
                    && xa == xb
            }
            _ => false,
        },
        (
            Some(SorobanAuthorizedFunctionType::CreateContractV2HostFn),
            Some(HostFunctionType::CreateContractV2),
        ) => match (
            &auth_fn.create_contract_v2_host_fn,
            &invoked_fn.create_contract_v2,
        ) {
            (Some(a), Some(b)) => {
                let (mut xa, mut xb) = (Vec::new(), Vec::new());
                write_create_contract_args_v2(&mut xa, a).is_ok()
                    && write_create_contract_args_v2(&mut xb, b).is_ok()
                    && xa == xb
            }
            _ => false,
        },
        _ => false,
    }
}

fn confirm_invoke_host_function_op(
    op: &InvokeHostFunctionOp,
    tx_source_account: &str,
    network_id: &[u8; 32],
) -> Result<()> {
    let function = &op.function;

    // the account whose signature authorizes the operation anyway: its
    // explicit source account, or the transaction's otherwise
    let source_account = op
        .source_account
        .as_deref()
        .filter(|s| !s.is_empty())
        .unwrap_or(tx_source_account);

    match HostFunctionType::try_from(function.r#type) {
        Ok(HostFunctionType::InvokeContract) => {
            let invoke = function
                .invoke_contract
                .as_ref()
                .ok_or(Error::DataError("Stellar: missing invoke_contract"))?;
            confirm_invoke_contract(invoke, network_id, source_account, None).c()?;
        }
        Ok(HostFunctionType::CreateContractV2) => {
            let create = function
                .create_contract_v2
                .as_ref()
                .ok_or(Error::DataError("Stellar: missing create_contract_v2"))?;
            confirm_create_contract(create, network_id, None).c()?;
        }
        Err(_) => return Err(Error::DataError("Stellar: unsupported host function type")),
    }

    // Auth entries fall into two kinds by credential type:
    //
    // - SOURCE_ACCOUNT credentials are authorized by the signature the device
    //   produces over the transaction envelope. Approving that signature
    //   approves these entries, so we must always show them for confirmation.
    //
    // - ADDRESS* credentials are authorized by a separate signature over the
    //   ENVELOPE_TYPE_SOROBAN_AUTHORIZATION* preimage, which must already be
    //   present in the entry at the time of signing the transaction. Entries
    //   of this type are therefore hidden behind an opt-in and only shown for
    //   information; the user does not need to review them to sign safely.
    let mut shown = 0usize;
    let mut non_src_entries: Vec<&SorobanAuthorizationEntry> = Vec::new();

    for auth_entry in &op.auth {
        if auth_entry.credentials.r#type
            == SorobanCredentialsType::SorobanCredentialsSourceAccount as i32
        {
            shown += 1;
            confirm_auth_entry(
                auth_entry,
                shown,
                network_id,
                source_account,
                is_root_auth_entry(auth_entry, function),
            )
            .c()?;
        } else {
            non_src_entries.push(auth_entry);
        }
    }

    if !non_src_entries.is_empty()
        && should_show_more(
            tr!("stellar__ext_auth"),
            tr!("stellar__ext_auth_message"),
            tr!("buttons__show_all"),
        )
        .c()?
    {
        for auth_entry in non_src_entries {
            shown += 1;
            confirm_auth_entry(
                auth_entry,
                shown,
                network_id,
                source_account,
                is_root_auth_entry(auth_entry, function),
            )
            .c()?;
        }
    }
    Ok(())
}

fn confirm_auth_entry(
    auth: &SorobanAuthorizationEntry,
    position: usize,
    network_id: &[u8; 32],
    source_account: &str,
    is_root: bool,
) -> Result<()> {
    let creds = &auth.credentials;
    let title = uformat!("{} #{}", tr!("words__authorization"), position);

    // SOURCE_ACCOUNT credentials authorize the tree through the effective
    // operation source; address credentials name their authorizing party.
    let authorizing_address = match SorobanCredentialsType::try_from(creds.r#type) {
        Ok(SorobanCredentialsType::SorobanCredentialsSourceAccount) => source_account,
        Ok(SorobanCredentialsType::SorobanCredentialsAddressV2) => {
            let credentials = creds
                .address_v2
                .as_ref()
                .ok_or(Error::DataError("Stellar: missing address_v2 credentials"))?;
            confirm_authorizing_address(&title, &credentials.address).c()?;
            credentials.address.as_str()
        }
        Ok(SorobanCredentialsType::SorobanCredentialsAddressWithDelegates) => {
            let credentials = creds
                .address_with_delegates
                .as_ref()
                .ok_or(Error::DataError(
                    "Stellar: missing address_with_delegates credentials",
                ))?;
            // The delegated signers themselves are not shown: like the nonce
            // and the signature, they are how this address established its
            // authorization, not what it authorizes.
            let address = credentials.address_credentials.address.as_str();
            confirm_authorizing_address(&title, address).c()?;
            address
        }
        Err(_) => return Err(Error::DataError("Stellar: unsupported credentials type")),
    };

    // Show the whole authorized invocation tree starting from its root (not
    // just the nested sub-invocations), so the user sees exactly what this
    // signature authorizes.
    confirm_invocation(
        &auth.root_invocation,
        &uformat!("#{}", position),
        network_id,
        authorizing_address,
        is_root,
    )
}

fn confirm_authorizing_address(title: &str, address: &str) -> Result<()> {
    confirm_address(
        title,
        address,
        Some(tr!("words__address")),
        "op_auth_entry_address",
        false,
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn price_formatting_matches_single_precision_python() {
        assert_eq!(format_price(1, 2), "0.5");
        assert_eq!(format_price(2, 1), "2.0");
        assert_eq!(format_price(1, 3), "0.3333333");
        assert_eq!(format_price(10, 1), "10.0");
        assert_eq!(format_price(3, 4), "0.75");
        assert_eq!(format_price(0, 5), "0.0");
        assert_eq!(format_price(1, 100_000), "1e-05");
        assert_eq!(format_price(123_456_789, 1), "1.234568e+08");
    }

    #[test]
    fn flags_are_listed_one_per_line() {
        assert_eq!(
            format_flags(FLAG_AUTH_REQUIRED | FLAG_AUTH_IMMUTABLE).unwrap(),
            "AUTH_REQUIRED\nAUTH_IMMUTABLE\n"
        );
        assert!(format_flags(8).is_err());
    }

    #[test]
    fn asset_type_is_not_native_for_alphanum() {
        let asset = Asset {
            r#type: crate::proto::stellar::AssetType::Alphanum4 as i32,
            code: None,
            issuer: None,
        };
        assert!(asset_has_issuer(&asset));
    }
}

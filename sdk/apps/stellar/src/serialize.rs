//! XDR serialization of the individual operations of a transaction.

use crate::{
    proto::stellar::{
        AccountMergeOp, AllowTrustOp, BumpSequenceOp, ChangeTrustOp, ClaimClaimableBalanceOp,
        CreateAccountOp, CreatePassiveSellOfferOp, HostFunction, InvokeHostFunctionOp,
        ManageBuyOfferOp, ManageDataOp, ManageSellOfferOp, PathPaymentStrictReceiveOp,
        PathPaymentStrictSendOp, PaymentOp, SetOptionsOp, SorobanAddressCredentials,
        SorobanAddressCredentialsWithDelegates, SorobanAuthorizationEntry, SorobanCredentials,
        SorobanDelegateSignature, host_function::HostFunctionType,
        soroban_credentials::SorobanCredentialsType,
    },
    writers::{
        Writer, asset_type, write_amount, write_asset, write_asset_code, write_bool,
        write_bytes_fixed, write_create_contract_args_v2, write_int64, write_invoke_contract_args,
        write_pubkey, write_sc_address, write_sc_val, write_soroban_authorized_invocation,
        write_string, write_uint32, write_uint64, write_vec,
    },
};
use trezor_app_sdk::{Error, Result, ResultExt};

pub fn write_account_merge_op(w: &mut dyn Writer, msg: &AccountMergeOp) -> Result<()> {
    write_pubkey(w, &msg.destination_account)
}

pub fn write_allow_trust_op(w: &mut dyn Writer, msg: &AllowTrustOp) -> Result<()> {
    // trustor account (the account being allowed to access the asset)
    write_pubkey(w, &msg.trusted_account).c()?;
    let ty = asset_type(msg.asset_type).c()?;
    write_uint32(w, msg.asset_type as u32);
    write_asset_code(w, ty, msg.asset_code.as_deref()).c()?;

    write_bool(w, msg.is_authorized);
    Ok(())
}

pub fn write_bump_sequence_op(w: &mut dyn Writer, msg: &BumpSequenceOp) {
    write_uint64(w, msg.bump_to);
}

pub fn write_change_trust_op(w: &mut dyn Writer, msg: &ChangeTrustOp) -> Result<()> {
    write_asset(w, &msg.asset).c()?;
    write_uint64(w, msg.limit);
    Ok(())
}

pub fn write_create_account_op(w: &mut dyn Writer, msg: &CreateAccountOp) -> Result<()> {
    write_pubkey(w, &msg.new_account).c()?;
    write_amount(w, msg.starting_balance)
}

pub fn write_create_passive_sell_offer_op(
    w: &mut dyn Writer,
    msg: &CreatePassiveSellOfferOp,
) -> Result<()> {
    write_asset(w, &msg.selling_asset).c()?;
    write_asset(w, &msg.buying_asset).c()?;
    write_amount(w, msg.amount).c()?;
    write_uint32(w, msg.price_n);
    write_uint32(w, msg.price_d);
    Ok(())
}

pub fn write_manage_data_op(w: &mut dyn Writer, msg: &ManageDataOp) -> Result<()> {
    let written = write_string(w, msg.key.as_bytes());
    if written > 64 {
        return Err(Error::DataError("Stellar: max length of a key is 64 bytes"));
    }
    // an empty value is the same as no value
    let value = msg.value.as_deref().filter(|v| !v.is_empty());
    write_bool(w, value.is_some());
    if let Some(value) = value {
        write_string(w, value);
    }
    Ok(())
}

pub fn write_manage_buy_offer_op(w: &mut dyn Writer, msg: &ManageBuyOfferOp) -> Result<()> {
    write_manage_offer_op_common(
        w,
        (
            &msg.selling_asset,
            &msg.buying_asset,
            msg.amount,
            msg.price_n,
            msg.price_d,
            msg.offer_id,
        ),
    )
}

pub fn write_manage_sell_offer_op(w: &mut dyn Writer, msg: &ManageSellOfferOp) -> Result<()> {
    write_manage_offer_op_common(
        w,
        (
            &msg.selling_asset,
            &msg.buying_asset,
            msg.amount,
            msg.price_n,
            msg.price_d,
            msg.offer_id,
        ),
    )
}

type ManageOffer<'a> = (
    &'a crate::proto::stellar::Asset,
    &'a crate::proto::stellar::Asset,
    i64,
    u32,
    u32,
    u64,
);

fn write_manage_offer_op_common(
    w: &mut dyn Writer,
    (selling, buying, amount, price_n, price_d, offer_id): ManageOffer<'_>,
) -> Result<()> {
    write_asset(w, selling).c()?;
    write_asset(w, buying).c()?;
    write_amount(w, amount).c()?; // amount to sell / buy
    write_uint32(w, price_n); // numerator
    write_uint32(w, price_d); // denominator
    write_uint64(w, offer_id);
    Ok(())
}

pub fn write_path_payment_strict_receive_op(
    w: &mut dyn Writer,
    msg: &PathPaymentStrictReceiveOp,
) -> Result<()> {
    write_asset(w, &msg.send_asset).c()?;
    write_amount(w, msg.send_max).c()?;
    write_pubkey(w, &msg.destination_account).c()?;

    write_asset(w, &msg.destination_asset).c()?;
    write_amount(w, msg.destination_amount).c()?;
    write_vec(w, &msg.paths, |w, asset| write_asset(w, asset))
}

pub fn write_path_payment_strict_send_op(
    w: &mut dyn Writer,
    msg: &PathPaymentStrictSendOp,
) -> Result<()> {
    write_asset(w, &msg.send_asset).c()?;
    write_amount(w, msg.send_amount).c()?;
    write_pubkey(w, &msg.destination_account).c()?;

    write_asset(w, &msg.destination_asset).c()?;
    write_amount(w, msg.destination_min).c()?;
    write_vec(w, &msg.paths, |w, asset| write_asset(w, asset))
}

pub fn write_payment_op(w: &mut dyn Writer, msg: &PaymentOp) -> Result<()> {
    write_pubkey(w, &msg.destination_account).c()?;
    write_asset(w, &msg.asset).c()?;
    write_amount(w, msg.amount)
}

pub fn write_set_options_op(w: &mut dyn Writer, msg: &SetOptionsOp) -> Result<()> {
    // inflation destination
    match &msg.inflation_destination_account {
        None => write_bool(w, false),
        Some(account) => {
            write_bool(w, true);
            write_pubkey(w, account).c()?;
        }
    }

    for option in [
        // clear flags
        msg.clear_flags,
        // set flags
        msg.set_flags,
        // account thresholds
        msg.master_weight,
        msg.low_threshold,
        msg.medium_threshold,
        msg.high_threshold,
    ] {
        match option {
            None => write_bool(w, false),
            Some(option) => {
                write_bool(w, true);
                write_uint32(w, option);
            }
        }
    }

    // home domain
    match &msg.home_domain {
        None => write_bool(w, false),
        Some(home_domain) => {
            write_bool(w, true);
            let written = write_string(w, home_domain.as_bytes());
            if written > 32 {
                return Err(Error::DataError(
                    "Stellar: max length of a home domain is 32 bytes",
                ));
            }
        }
    }

    // signer
    match msg.signer_type {
        None => write_bool(w, false),
        Some(signer_type) => {
            let (Some(signer_key), Some(signer_weight)) = (&msg.signer_key, msg.signer_weight)
            else {
                return Err(Error::DataError(
                    "Stellar: signer_type, signer_key, signer_weight must be set together",
                ));
            };
            write_bool(w, true);
            write_uint32(w, signer_type as u32);
            write_bytes_fixed(w, signer_key, 32).c()?;
            write_uint32(w, signer_weight);
        }
    }
    Ok(())
}

pub fn write_claim_claimable_balance_op(
    w: &mut dyn Writer,
    msg: &ClaimClaimableBalanceOp,
) -> Result<()> {
    write_claimable_balance_id(w, &msg.balance_id)
}

pub fn write_account(w: &mut dyn Writer, source_account: Option<&str>) -> Result<()> {
    match source_account {
        None => write_bool(w, false),
        Some(account) => {
            write_bool(w, true);
            write_pubkey(w, account).c()?;
        }
    }
    Ok(())
}

fn write_claimable_balance_id(w: &mut dyn Writer, claimable_balance_id: &[u8]) -> Result<()> {
    if claimable_balance_id.len() != 36 {
        // 4 bytes type + 32 bytes data
        return Err(Error::DataError(
            "Stellar: invalid claimable balance id length",
        ));
    }
    if claimable_balance_id[..4] != [0, 0, 0, 0] {
        // CLAIMABLE_BALANCE_ID_TYPE_V0
        return Err(Error::DataError(
            "Stellar: invalid claimable balance id, unknown type",
        ));
    }
    write_bytes_fixed(w, claimable_balance_id, 36)
}

pub fn write_invoke_host_function_op(w: &mut dyn Writer, msg: &InvokeHostFunctionOp) -> Result<()> {
    write_host_function(w, &msg.function).c()?;
    write_vec(w, &msg.auth, |w, entry| {
        write_soroban_authorization_entry(w, entry)
    })
}

fn write_host_function(w: &mut dyn Writer, msg: &HostFunction) -> Result<()> {
    let ty = HostFunctionType::try_from(msg.r#type)
        .map_err(|_| Error::DataError("Stellar: unsupported host function type"))?;
    write_uint32(w, msg.r#type as u32);
    match ty {
        HostFunctionType::InvokeContract => {
            let args = msg
                .invoke_contract
                .as_ref()
                .ok_or(Error::DataError("Stellar: missing invoke_contract"))?;
            write_invoke_contract_args(w, args)
        }
        HostFunctionType::CreateContractV2 => {
            let args = msg
                .create_contract_v2
                .as_ref()
                .ok_or(Error::DataError("Stellar: missing create_contract_v2"))?;
            write_create_contract_args_v2(w, args)
        }
    }
}

fn write_soroban_authorization_entry(
    w: &mut dyn Writer,
    msg: &SorobanAuthorizationEntry,
) -> Result<()> {
    write_soroban_credentials(w, &msg.credentials).c()?;
    write_soroban_authorized_invocation(w, &msg.root_invocation)
}

fn write_soroban_credentials(w: &mut dyn Writer, msg: &SorobanCredentials) -> Result<()> {
    let ty = SorobanCredentialsType::try_from(msg.r#type)
        .map_err(|_| Error::DataError("Stellar: unsupported credentials type"))?;
    write_uint32(w, msg.r#type as u32);
    match ty {
        SorobanCredentialsType::SorobanCredentialsSourceAccount => Ok(()), // void
        SorobanCredentialsType::SorobanCredentialsAddressV2 => {
            let credentials = msg
                .address_v2
                .as_ref()
                .ok_or(Error::DataError("Stellar: missing address credentials"))?;
            write_soroban_address_credentials(w, credentials)
        }
        SorobanCredentialsType::SorobanCredentialsAddressWithDelegates => {
            let credentials = msg.address_with_delegates.as_ref().ok_or(Error::DataError(
                "Stellar: missing address credentials with delegates",
            ))?;
            write_soroban_address_credentials_with_delegates(w, credentials)
        }
    }
}

fn write_soroban_address_credentials(
    w: &mut dyn Writer,
    msg: &SorobanAddressCredentials,
) -> Result<()> {
    write_sc_address(w, &msg.address).c()?;
    write_int64(w, msg.nonce);
    write_uint32(w, msg.signature_expiration_ledger);
    write_sc_val(w, &msg.signature)
}

fn write_soroban_address_credentials_with_delegates(
    w: &mut dyn Writer,
    msg: &SorobanAddressCredentialsWithDelegates,
) -> Result<()> {
    write_soroban_address_credentials(w, &msg.address_credentials).c()?;
    write_vec(w, &msg.delegates, |w, delegate| {
        write_soroban_delegate_signature(w, delegate)
    })
}

fn write_soroban_delegate_signature(
    w: &mut dyn Writer,
    msg: &SorobanDelegateSignature,
) -> Result<()> {
    write_sc_address(w, &msg.address).c()?;
    write_sc_val(w, &msg.signature).c()?;
    write_vec(w, &msg.nested_delegates, |w, delegate| {
        write_soroban_delegate_signature(w, delegate)
    })
}

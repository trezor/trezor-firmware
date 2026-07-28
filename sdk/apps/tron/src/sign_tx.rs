use crate::sc_constants::{
    SC_ARGUMENT_ADDRESS_BYTES, SC_ARGUMENT_BYTES, SC_FUNC_SIG_APPROVE, SC_FUNC_SIG_BYTES,
    SC_FUNC_SIG_TRANSFER,
};
use crate::{
    alloc_types::{String, Vec, vec},
    common::get_pubkey_hash,
    common::{COIN, SLIP44_ID, get_encoded_address},
    consts::token_by_address,
    layout::{
        confirm_blob, confirm_freeze_operations, confirm_known_trc20_smart_contract,
        confirm_trx_transfer, confirm_unknown_smart_contract,
    },
    paths::{Bip32Path, PATTERNS_ADDRESS},
    proto::{
        common::button_request::ButtonRequestType,
        messages::MessageType,
        tron::{
            ContractRequest, FreezeBalanceV2Contract, RawTransaction, SignTx, Signature,
            TransferContract, TriggerSmartContract, UnfreezeBalanceV2Contract,
            raw_transaction::{
                RawContract,
                raw_contract::{RawContractType, RawParameter},
            },
        },
    },
};
use prost::Message;
use trezor_app_sdk::{
    CORE_SERVICE, Error, IpcMessage, Result, service::CoreIpcService, unwrap, util::Timeout,
};
use trezor_app_sdk::{ResultExt, crypto, ui};

// Maximum chain_id which returns the full signature_v (which must fit into an uint32).
// chain_ids larger than this will only return one bit and the caller must recalculate
// the full value: v = 2 * chain_id + 35 + v_bit
const MAX_CHAIN_ID: u64 = (0xFFFF_FFFF - 36) / 2;

pub fn sign_tx(mut msg: SignTx) -> Result<Signature> {
    let dp = Bip32Path::from_slice(&msg.address_n);

    // crypto::verify_derivation_path(&dp.as_ref(), None, None, None)
    //     .context("Failed to verify derivation path")?;

    validate_tx_fields(&msg).c()?;

    let (contract_type, contract_bytes) = request_contract().c()?;

    let account_name = dp.get_account_name(COIN, &PATTERNS_ADDRESS, SLIP44_ID);
    let account_str = dp.format_path();

    let mut signer_address = [0u8; 21];
    signer_address[0] = 0x41;
    signer_address[1..].copy_from_slice(&get_pubkey_hash(&dp).c()?);

    let fee_limit = msg.fee_limit.unwrap_or(0);
    let raw_contract = process_contract(
        contract_type,
        contract_bytes,
        fee_limit,
        (account_name.as_deref(), account_str.as_str()),
        &get_encoded_address(&signer_address)?,
    )?;

    let raw_tx = RawTransaction {
        ref_block_bytes: msg.ref_block_bytes,
        ref_block_hash: msg.ref_block_hash,
        expiration: msg.expiration,
        data: msg.data,
        contract: vec![raw_contract],
        timestamp: msg.timestamp,
        fee_limit: msg.fee_limit,
    };
    let raw_tx_serialized = raw_tx.encode_to_vec();

    let w_hash = crypto::Sha256::new(Some(&raw_tx_serialized)).digest();

    // https://tronprotocol.github.io/documentation-en/mechanism-algorithm/account/#algorithm
    let sig = crypto::sign_typed_hash(&msg.address_n, &w_hash, None, None, None, false)?;

    let mut signature = Vec::with_capacity(65);
    signature.extend_from_slice(&sig[1..65]);
    signature.push(sig[0]);

    ui::show_success(ui::ShowSuccess::new(
        tr!("words__title_done"),
        tr!("send__transaction_signed"),
        tr!("instructions__continue_in_app"),
        Some(3200),
        None,
        ButtonRequestType::Other.into(),
    ))?;

    // Ok(Signature(signature = signature))
    Err(Error::Cancelled)
}

fn validate_tx_fields(msg: &SignTx) -> Result<()> {
    const _MAX_DATA_LENGTH: usize = 256;
    const _MAX_FEE_LIMIT: u64 = 15_000_000_000; // TRON: Maximum Fee limit in SUN.

    //  https://developers.tron.network/docs/set-feelimit
    if let Some(fee_limit) = msg.fee_limit {
        if fee_limit > _MAX_FEE_LIMIT {
            return Err(Error::DataError("Tron: fees too high"));
        }
    }

    // It is not necessary for it to be UTF-8 encoded but all applications using it use it as a Note to be attached with the transaction.
    if let Some(data) = &msg.data {
        if !data.is_empty() {
            if data.len() > _MAX_DATA_LENGTH {
                return Err(Error::DataError("Tron: data field too long"));
            }

            confirm_blob(
                tr!("words__note"),
                String::from_utf8_lossy(data).as_ref(),
                None,
                None,
                "tron/note",
                ButtonRequestType::Other.into(),
                false,
                None,
                Some(tr!("buttons__continue")),
                false,
                false,
                false,
            )?;
        }
    }

    Ok(())
}

fn process_contract(
    contract_type: RawContractType,
    contract_bytes: Vec<u8>,
    fee_limit: u64,
    account_details: (Option<&str>, &str),
    signer_address: &str,
) -> Result<RawContract> {
    match contract_type {
        RawContractType::TransferContract => {
            let c = TransferContract::decode(contract_bytes.as_slice())
                .map_err(|_| Error::DataError("Tron: failed to decode TransferContract"))?;
            const INT64_MAX: u64 = i64::MAX as u64;

            let owner_address = get_encoded_address(&c.owner_address)?;
            if c.amount > INT64_MAX {
                return Err(Error::DataError("Tron: invalid transfer amount"));
            }
            confirm_trx_transfer(&c, account_details)?;
        }
        RawContractType::TriggerSmartContract => {
            let c = TriggerSmartContract::decode(contract_bytes.as_slice())
                .map_err(|_| Error::DataError("Tron: failed to decode TriggerSmartContract"))?;
            process_smart_contract(&c, fee_limit)?;
        }

        RawContractType::FreezeBalanceV2Contract => {
            let mut c = FreezeBalanceV2Contract::decode(contract_bytes.as_slice())
                .map_err(|_| Error::DataError("Tron: failed to decode FreezeBalanceV2Contract"))?;

            c.resource.get_or_insert_default();

            confirm_freeze_operations(
                &c.owner_address,
                c.balance,
                unwrap!(c.resource),
                tr!("ethereum__staking_stake"),
            )?;
        }

        RawContractType::UnfreezeBalanceV2Contract => {
            let mut c =
                UnfreezeBalanceV2Contract::decode(contract_bytes.as_slice()).map_err(|_| {
                    Error::DataError("Tron: failed to decode UnfreezeBalanceV2Contract")
                })?;
            c.resource.get_or_insert_default();

            confirm_freeze_operations(
                &c.owner_address,
                c.balance,
                unwrap!(c.resource),
                tr!("ethereum__staking_unstake"),
            )?;
        }

        //       // RawContractType::WithdrawExpireUnfreezeContract => {
        //       //     layout::confirm_claim(
        //       //         if is_different_owner {
        //       //             owner_address.as_deref()
        //       //         } else {
        //       //             None
        //       //         },
        //       //         account_details,
        //       //         tr!("tron__claim_unfrozen_balance"),
        //       //     )?;
        //       // }

        //       // RawContractType::WithdrawBalanceContract => {
        //       //     layout::confirm_claim(
        //       //         if is_different_owner {
        //       //             owner_address.as_deref()
        //       //         } else {
        //       //             None
        //       //         },
        //       //         account_details,
        //       //         tr!("tron__claim_voting_rewards"),
        //       //     )?;
        //       // }

        //       RawContractType::VoteWitnessContract => {
        //           let c = VoteWitnessContract::decode(data.as_slice())
        //               .map_err(|_| Error::DataError("Tron: failed to decode VoteWitnessContract"))?;
        //           if c.votes.len() > 9 {
        //               return Err(Error::DataError("Tron: too many votes"));
        //           }
        //           layout::confirm_votes(&c)?;
        //       }
        _ => todo!(),
    }

    Ok(RawContract {
        r#type: contract_type as i32,
        parameter: RawParameter {
            type_url: "".into(),
            value: contract_bytes,
        },
    })
}

pub(crate) fn request_contract() -> Result<(RawContractType, Vec<u8>)> {
    let req = ContractRequest {};

    let req_bytes = req.encode_to_vec();
    let message = IpcMessage::new(MessageType::ContractRequest as u16, &req_bytes);
    let result = CORE_SERVICE.call(CoreIpcService::WireContinue, &message, Timeout::max())?;

    let data = result.data().to_vec();

    let contract_type = match result.id() as i32 {
        x if x == MessageType::TransferContract as i32 => RawContractType::TransferContract,
        x if x == MessageType::VoteWitnessContract as i32 => RawContractType::VoteWitnessContract,
        x if x == MessageType::TriggerSmartContract as i32 => RawContractType::TriggerSmartContract,
        x if x == MessageType::FreezeBalanceV2Contract as i32 => {
            RawContractType::FreezeBalanceV2Contract
        }
        x if x == MessageType::UnfreezeBalanceV2Contract as i32 => {
            RawContractType::UnfreezeBalanceV2Contract
        }
        x if x == MessageType::WithdrawUnfreeze as i32 => {
            RawContractType::WithdrawExpireUnfreezeContract
        }
        x if x == MessageType::WithdrawBalance as i32 => RawContractType::WithdrawBalanceContract,
        _ => return Err(Error::InvalidMessage),
    };

    Ok((contract_type, data))
}

fn process_smart_contract(contract: &TriggerSmartContract, fee_limit: u64) -> Result<()> {
    if process_known_trc20_contract(contract, fee_limit)? {
        return Ok(());
    } else {
        confirm_unknown_smart_contract(&contract, fee_limit)?;
        Ok(())
    }
}

/// Returns false when the contract is unrecoginsed. i.e. not (Transfer and known TRC-20)
fn process_known_trc20_contract(contract: &TriggerSmartContract, fee_limit: u64) -> Result<bool> {
    let token_info = token_by_address(&contract.contract_address);
    if token_info.is_none() || contract.data.len() != (SC_ARGUMENT_BYTES * 2 + SC_FUNC_SIG_BYTES) {
        return Ok(false);
    }

    let (token_decimals, token_symbol) = unwrap!(token_info);

    let (func_sig, rest) = contract.data.split_at(SC_FUNC_SIG_BYTES);
    if func_sig != &SC_FUNC_SIG_APPROVE && func_sig != &SC_FUNC_SIG_TRANSFER {
        return Ok(false);
    }

    let (address_arg, rest) = rest.split_at(SC_ARGUMENT_BYTES);
    if !address_arg[..SC_ARGUMENT_BYTES - SC_ARGUMENT_ADDRESS_BYTES]
        .iter()
        .all(|&byte| byte == 0)
    {
        // invalid address padding in contract data
        return Ok(false);
    }

    // TRON truncates the mandatory prefix \x41 from addresses in data
    let recipient = [
        &[0x41],
        &address_arg[SC_ARGUMENT_BYTES - SC_ARGUMENT_ADDRESS_BYTES..],
    ]
    .concat();

    let (amount_arg, _) = rest.split_at(SC_ARGUMENT_BYTES);

    confirm_known_trc20_smart_contract(
        func_sig == SC_FUNC_SIG_APPROVE,
        &recipient,
        amount_arg,
        fee_limit,
        token_decimals,
        token_symbol,
    )?;

    Ok(true)
}

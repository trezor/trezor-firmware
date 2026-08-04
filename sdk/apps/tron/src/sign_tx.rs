use crate::ProstCodec;
use crate::sc_constants::{
    SC_ARGUMENT_ADDRESS_BYTES, SC_ARGUMENT_BYTES, SC_FUNC_SIG_APPROVE, SC_FUNC_SIG_BYTES,
    SC_FUNC_SIG_TRANSFER,
};
use crate::{
    alloc_types::{String, Vec, vec},
    common::get_pubkey_hash,
    common::{COIN, SLIP44_ID, get_encoded_address},
    consts::{TYPE_URL_TEMPLATE, token_by_address},
    layout::{
        confirm_blob, confirm_claim, confirm_delegate_resource, confirm_freeze_operations,
        confirm_known_trc20_smart_contract, confirm_tron_voting, confirm_trx_transfer,
        confirm_undelegate_resource, confirm_unknown_smart_contract,
    },
    paths::{Bip32Path, PATTERNS_ADDRESS},
    proto::{
        common::button_request::ButtonRequestType,
        messages::MessageType,
        tron::{
            ContractRequest, DelegateResourceContract, FreezeBalanceV2Contract, RawTransaction,
            ResourceCode, SignTx, Signature, TransferContract, TriggerSmartContract,
            UnDelegateResourceContract, UnfreezeBalanceV2Contract, VoteWitnessContract,
            WithdrawBalance, WithdrawUnfreeze,
            raw_transaction::{
                RawContract,
                raw_contract::{RawContractType, RawParameter},
            },
        },
    },
    uformat,
};
use prost::Message;
use trezor_app_sdk::{Error, Result, ResultExt, WireEncode, unwrap, wire_request_raw};
use trezor_app_sdk::{
    crypto,
    crypto::{HasherExt as _, HashingAlgorithm},
    ui::{self, Property},
};

// Maximum chain_id which returns the full signature_v (which must fit into an uint32).
// chain_ids larger than this will only return one bit and the caller must recalculate
// the full value: v = 2 * chain_id + 35 + v_bit
const MAX_CHAIN_ID: u64 = (0xFFFF_FFFF - 36) / 2;

const INT64_MAX: u64 = i64::MAX as u64;

// https://github.com/tronprotocol/java-tron/blob/1691fddbd4f8df35df31713cc7772273d7d03360/actuator/src/main/java/org/tron/core/actuator/DelegateResourceActuator.java#L149
const MINIMUM_DELEGATION_BALANCE: u64 = 1_000_000; // 1 TRX in SUN
// Network parameter value getMaxDelegateLockPeriod = 864000 (30D) via api.trongrid.io/wallet/getchainparameters
// But we're leaving room for future changes since network will reject invalid values anyway.
// 1 block per 3 seconds = 20 blocks per minute.
const MAX_LOCK_PERIOD_BLOCKS: u64 = 365 * 24 * 60 * 20;
// Network defined. Not a protobuf default (proto3 doesn't support [default = 81400] and Tron uses proto3).
// 3 days. TRON's default lock period when lock is true but period unspecified.
const DEFAULT_LOCK_PERIOD_BLOCKS: u64 = 86400;

pub fn sign_tx(msg: SignTx) -> Result<Signature> {
    let dp = Bip32Path::from_slice(&msg.address_n);

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
        &get_encoded_address(&signer_address).c()?,
        msg.chunkify.unwrap_or(false),
    )
    .c()?;

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

    let mut hasher = crypto::get_hasher(HashingAlgorithm::Sha256);
    hasher.update(raw_tx_serialized.as_slice());
    let w_hash: [u8; 32] = hasher.finalize().as_slice().try_into().unwrap();

    // https://tronprotocol.github.io/documentation-en/mechanism-algorithm/account/#algorithm
    let sig = crypto::sign_typed_hash(&msg.address_n, &w_hash, None, None, None, false).c()?;

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
    ))
    .c()?;

    Ok(Signature { signature })
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
                Some(tr!("buttons__continue")),
                None,
                false,
                false,
                false,
            )
            .c()?;
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
    chunkify: bool,
) -> Result<RawContract> {
    let value = match contract_type {
        RawContractType::TransferContract => {
            let c = TransferContract::decode(contract_bytes.as_slice())
                .map_err(|_| Error::DataError("Tron: failed to decode TransferContract"))
                .c()?;
            if c.amount > INT64_MAX {
                return Err(Error::DataError("Tron: invalid transfer amount"));
            }
            confirm_trx_transfer(&c, account_details, chunkify)?;
            contract_bytes
        }
        RawContractType::TriggerSmartContract => {
            let c = TriggerSmartContract::decode(contract_bytes.as_slice())
                .map_err(|_| Error::DataError("Tron: failed to decode TriggerSmartContract"))
                .c()?;
            process_smart_contract(&c, fee_limit, chunkify)?;
            contract_bytes
        }

        RawContractType::FreezeBalanceV2Contract => {
            let mut c = FreezeBalanceV2Contract::decode(contract_bytes.as_slice())
                .map_err(|_| Error::DataError("Tron: failed to decode FreezeBalanceV2Contract"))
                .c()?;

            confirm_freeze_operations(
                &c.owner_address,
                c.balance,
                c.resource().into(),
                tr!("ethereum__staking_stake"),
                chunkify,
            )
            .c()?;

            // TRON protocol uses proto3, which omits fields with default values from
            // serialization. Since BANDWIDTH=0 is the default, we must set resource=None
            // to match proto3 encoding and produce the correct transaction hash.
            if c.resource() == ResourceCode::Bandwidth {
                c.resource = None;
            }
            FreezeBalanceV2Contract::encode_to_vec(&c)
        }

        RawContractType::UnfreezeBalanceV2Contract => {
            let mut c = UnfreezeBalanceV2Contract::decode(contract_bytes.as_slice())
                .map_err(|_| Error::DataError("Tron: failed to decode UnfreezeBalanceV2Contract"))
                .c()?;

            confirm_freeze_operations(
                &c.owner_address,
                c.balance,
                c.resource().into(),
                tr!("ethereum__staking_unstake"),
                chunkify,
            )
            .c()?;
            // TRON protocol uses proto3, which omits fields with default values from
            // serialization. Since BANDWIDTH=0 is the default, we must set resource=None
            // to match proto3 encoding and produce the correct transaction hash.
            if c.resource() == ResourceCode::Bandwidth {
                c.resource = None;
            }
            UnfreezeBalanceV2Contract::encode_to_vec(&c)
        }

        RawContractType::WithdrawExpireUnfreezeContract => {
            let c = WithdrawUnfreeze::decode(contract_bytes.as_slice())
                .map_err(|_| Error::DataError("Tron: failed to decode WithdrawUnfreeze"))
                .c()?;
            let owner_address = get_encoded_address(&c.owner_address).c()?;
            let is_different_owner = owner_address != signer_address;

            confirm_claim(
                if is_different_owner {
                    Some(&owner_address)
                } else {
                    None
                },
                account_details,
                tr!("tron__claim_unfrozen_balance"),
                chunkify,
            )
            .c()?;
            contract_bytes
        }

        RawContractType::WithdrawBalanceContract => {
            let c = WithdrawBalance::decode(contract_bytes.as_slice())
                .map_err(|_| Error::DataError("Tron: failed to decode WithdrawBalance"))
                .c()?;
            let owner_address = get_encoded_address(&c.owner_address).c()?;
            let is_different_owner = owner_address != signer_address;
            confirm_claim(
                if is_different_owner {
                    Some(&owner_address)
                } else {
                    None
                },
                account_details,
                tr!("tron__claim_voting_rewards"),
                chunkify,
            )
            .c()?;
            contract_bytes
        }

        RawContractType::DelegateResourceContract => {
            let mut c = DelegateResourceContract::decode(contract_bytes.as_slice())
                .map_err(|_| Error::DataError("Tron: failed to decode DelegateResourceContract"))
                .c()?;

            let lock = c.lock.unwrap_or(false);
            let raw_lock_period = c.lock_period;

            let mut lock_period = None;
            // Contract specific validation
            if lock {
                let period = match raw_lock_period {
                    None | Some(0) => DEFAULT_LOCK_PERIOD_BLOCKS,
                    Some(period) => period,
                };
                if period > MAX_LOCK_PERIOD_BLOCKS {
                    return Err(Error::DataError("Tron: Invalid lock period (Max 365d)"));
                }
                lock_period = Some(period);
            } else if raw_lock_period.is_some() {
                // Tron technically allows this (rejects the lock, encodes the value) but we would
                // rather the host not send inconsistent values.
                return Err(Error::DataError(
                    "Tron: lock_period should not be set when lock is false",
                ));
            }
            if c.balance < MINIMUM_DELEGATION_BALANCE {
                return Err(Error::DataError("Tron: Amount too low (Min 1 TRX)"));
            }

            confirm_delegate_resource(
                &c.receiver_address,
                c.balance,
                c.resource().into(),
                lock_period,
            )
            .c()?;

            // Match proto3 encoding: omit fields that equal their default values
            if c.resource() == ResourceCode::Bandwidth {
                c.resource = None;
            }
            c.lock = if lock { Some(true) } else { None };
            if !lock {
                c.lock_period = None;
            }
            DelegateResourceContract::encode_to_vec(&c)
        }

        RawContractType::UnDelegateResourceContract => {
            let mut c = UnDelegateResourceContract::decode(contract_bytes.as_slice())
                .map_err(|_| Error::DataError("Tron: failed to decode UnDelegateResourceContract"))
                .c()?;

            confirm_undelegate_resource(&c.receiver_address, c.balance, c.resource().into()).c()?;

            // Match proto3 encoding: omit fields that equal their default values
            if c.resource() == ResourceCode::Bandwidth {
                c.resource = None;
            }
            UnDelegateResourceContract::encode_to_vec(&c)
        }

        RawContractType::VoteWitnessContract => {
            let c = VoteWitnessContract::decode(contract_bytes.as_slice())
                .map_err(|_| Error::DataError("Tron: failed to decode VoteWitnessContract"))
                .c()?;
            if c.votes.len() > 9 {
                return Err(Error::DataError("Tron: too many votes"));
            }
            confirm_votes(&c).c()?;
            contract_bytes
        }
    };

    Ok(RawContract {
        r#type: contract_type as i32,
        parameter: RawParameter {
            type_url: uformat!("{}{}", TYPE_URL_TEMPLATE, contract_type.as_str_name()).into(),
            value,
        },
    })
}

pub(crate) fn request_contract() -> Result<(RawContractType, Vec<u8>)> {
    let req_bytes = ProstCodec::encode(&ContractRequest {});
    let (id, data) = wire_request_raw(&req_bytes, MessageType::ContractRequest as u16).c()?;

    let contract_type = match (id as i32).try_into() {
        Ok(MessageType::TransferContract) => RawContractType::TransferContract,
        Ok(MessageType::VoteWitnessContract) => RawContractType::VoteWitnessContract,
        Ok(MessageType::TriggerSmartContract) => RawContractType::TriggerSmartContract,
        Ok(MessageType::FreezeBalanceV2Contract) => RawContractType::FreezeBalanceV2Contract,
        Ok(MessageType::UnfreezeBalanceV2Contract) => RawContractType::UnfreezeBalanceV2Contract,
        Ok(MessageType::WithdrawUnfreeze) => RawContractType::WithdrawExpireUnfreezeContract,
        Ok(MessageType::WithdrawBalance) => RawContractType::WithdrawBalanceContract,
        Ok(MessageType::DelegateResourceContract) => RawContractType::DelegateResourceContract,
        Ok(MessageType::UnDelegateResourceContract) => RawContractType::UnDelegateResourceContract,
        _ => return Err(Error::InvalidMessage),
    };

    Ok((contract_type, data))
}

fn process_smart_contract(
    contract: &TriggerSmartContract,
    fee_limit: u64,
    chunkify: bool,
) -> Result<()> {
    let mut trx_value = None;
    if let Some(call_value) = contract.call_value.filter(|&value| value != 0) {
        if call_value > INT64_MAX {
            return Err(Error::DataError("Tron: invalid call value"));
        }
        trx_value = Some(call_value);
    }
    if process_known_trc20_contract(contract, fee_limit, trx_value, chunkify).c()? {
        return Ok(());
    } else {
        confirm_unknown_smart_contract(contract, fee_limit, trx_value, chunkify).c()?;
        Ok(())
    }
}

/// Returns false when the contract is unrecoginsed. i.e. not (Transfer and known TRC-20)
fn process_known_trc20_contract(
    contract: &TriggerSmartContract,
    fee_limit: u64,
    trx_value: Option<u64>,
    chunkify: bool,
) -> Result<bool> {
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
        trx_value,
        chunkify,
    )
    .c()?;

    Ok(true)
}

fn confirm_votes(contract: &VoteWitnessContract) -> Result<()> {
    let votes_label = uformat!("\n{}", tr!("words__votes"));

    let mut addresses = Vec::with_capacity(contract.votes.len());
    let mut counts = Vec::with_capacity(contract.votes.len());
    for vote in &contract.votes {
        addresses.push(get_encoded_address(&vote.address)?);
        counts.push(uformat!("{}", vote.count));
    }

    let mut voting_list = Vec::new();
    for (address, count) in addresses.iter().zip(counts.iter()) {
        voting_list.push(Property::mono(tr!("words__address"), address));
        voting_list.push(Property::plain(&votes_label, count));
    }

    confirm_tron_voting(&voting_list).c()?;
    Ok(())
}

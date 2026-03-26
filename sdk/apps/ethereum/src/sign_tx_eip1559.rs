use crate::{
    common::{
        SC_ARGUMENT_ADDRESS_BYTES, SC_ARGUMENT_BYTES, SC_FUNC_APPROVE_REVOKE_AMOUNT,
        SC_FUNC_SIG_BYTES, addresses_accounting, addresses_pool, require_confirm_address,
        require_confirm_approve, require_confirm_claim, require_confirm_other_data,
        require_confirm_payment_request, require_confirm_stake, require_confirm_tx,
        require_confirm_unstake, sc_func_sig_approve, sc_func_sig_claim, sc_func_sig_stake,
        sc_func_sig_transfer, sc_func_sig_unstake, send_request_chunk,
    },
    definitions::Definitions,
    helpers::{
        address_from_bytes, bytes_from_address, format_ethereum_amount, get_fee_items_eip1559,
    },
    keychain::{Keychain, PATTERNS_ADDRESS, schemas_from_network},
    paths::{Bip32Path, unharden},
    payment_request::PaymentRequestVerifier,
    proto::{
        common::button_request::ButtonRequestType,
        definitions::{EthereumNetworkInfo, EthereumTokenInfo},
        ethereum::{
            EthereumSignTxEip1559, EthereumTxRequest, ethereum_sign_tx_eip1559::EthereumAccessList,
        },
    },
    rlp::{self, RLPItem},
    tokens,
};
#[cfg(not(test))]
use alloc::{string::String, vec, vec::Vec};
use primitive_types::U256;
#[cfg(test)]
use std::{string::String, vec, vec::Vecs};
use trezor_app_sdk::{Error, Result, crypto, info, ui, unwrap};

const TX_TYPE: u32 = 2;

pub fn sign_tx_eip1559(mut msg: EthereumSignTxEip1559) -> Result<EthereumTxRequest> {
    msg.to.get_or_insert_default();
    msg.data_initial_chunk.get_or_insert_default();

    assert!(msg.to.is_some());
    assert!(msg.data_initial_chunk.is_some());

    let to = msg.to.as_deref().ok_or(Error::DataError)?;
    let data_initial_chunk = msg.data_initial_chunk.as_deref().ok_or(Error::DataError)?;

    info!("Signing transaction");
    let dp = Bip32Path::from_slice(&msg.address_n);

    info!("encoding definitions");

    let definitions = Definitions::from_encoded(
        msg.definitions
            .as_ref()
            .and_then(|d| d.encoded_network.as_ref().map(|v| v.as_slice())),
        msg.definitions
            .as_ref()
            .and_then(|d| d.encoded_token.as_ref().map(|v| v.as_slice())),
        Some(msg.chain_id),
        None,
    )
    .map_err(|_| Error::DataError)?;

    info!("setting up schemas");

    let schemas = schemas_from_network(&PATTERNS_ADDRESS, definitions.slip44())?;
    info!("setting up keychain");
    let keychain = Keychain::new(schemas);

    // check
    if msg.max_gas_fee.len() + msg.gas_limit.len() > 30 {
        // TODO: proper error handling: fee overflow
        return Err(Error::DataError);
    }
    if msg.max_priority_fee.len() + msg.gas_limit.len() > 30 {
        // TODO: proper error handling: fee overflow
        return Err(Error::DataError);
    }

    info!("checking common fields");
    check_common_fields(&msg)?;

    // have a user confirm signing
    dp.validate(&keychain)?;

    let address_bytes = bytes_from_address(to)?;

    // TODO: better implement parsing int value from bytes
    assert!(msg.gas_limit.len() <= 32);
    let max_gas_fee = U256::from_big_endian(&msg.max_gas_fee);

    // TODO: better implement parsing int value from bytes
    assert!(msg.max_priority_fee.len() <= 32);
    let max_priority_fee = U256::from_big_endian(&msg.max_priority_fee);

    // TODO: better implement parsing int value from bytes
    assert!(msg.gas_limit.len() <= 32);
    let gas_limit = U256::from_big_endian(&msg.gas_limit);
    let maximum_fee =
        format_ethereum_amount(max_gas_fee * gas_limit, None, definitions.network(), false);
    let fee_items = get_fee_items_eip1559(
        max_gas_fee,
        max_priority_fee,
        gas_limit,
        definitions.network(),
    );

    let fee_items_ref: Vec<(&str, &str, bool)> = fee_items
        .iter()
        .map(|(k, v, mono)| (k.as_str(), v.as_str(), *mono))
        .collect();

    info!("payment request verifier");
    let payment_req_verifier = if let Some(req) = &msg.payment_req {
        info!("slip 44 id");
        let slip44_id = unharden(msg.address_n[1]);
        info!(
            "creating payment request verifier with slip44 id {}",
            slip44_id
        );
        Some(PaymentRequestVerifier::new(req, slip44_id)?)
    } else {
        None
    };

    info!("confirming transaction data");

    confirm_tx_data(
        &msg,
        &definitions,
        &address_bytes,
        &maximum_fee,
        &fee_items_ref,
        msg.data_length,
        payment_req_verifier,
    )?;

    ui::init_progress(None, Some("Signing transaction..."), false, false)?;
    ui::update_progress(None, 100)?;

    // sign
    let mut data = Vec::new();
    data.extend_from_slice(data_initial_chunk);
    let mut data_left = msg.data_length - data_initial_chunk.len() as u32;

    // Calculate total RLP length
    let total_length = get_total_length(&msg, msg.data_length)?;
    info!("total RLP length: {}", total_length);

    let mut rlp_buffer = Vec::new();

    rlp::write(&mut rlp_buffer, &RLPItem::Int(TX_TYPE.into()));

    info!("writing RLP header");
    rlp::write_header(&mut rlp_buffer, total_length, rlp::LIST_HEADER_BYTE, None);

    // Write transaction fields
    let fields: Vec<RLPItem> = vec![
        RLPItem::Int(msg.chain_id.into()),
        RLPItem::Bytes(&msg.nonce),
        RLPItem::Bytes(&msg.max_priority_fee),
        RLPItem::Bytes(&msg.max_gas_fee),
        RLPItem::Int(gas_limit),
        RLPItem::Bytes(&address_bytes),
        RLPItem::Bytes(&msg.value),
    ];

    for field in &fields {
        rlp::write(&mut rlp_buffer, field);
    }

    // Write data field
    if data_left == 0 {
        info!("writing RLP data field");
        rlp::write(&mut rlp_buffer, &RLPItem::Bytes(&data));
    } else {
        info!("writing RLP data header");
        rlp::write_header(
            &mut rlp_buffer,
            msg.data_length,
            rlp::STRING_HEADER_BYTE,
            Some(&data),
        );
        rlp_buffer.extend_from_slice(&data);
    }

    ui::update_progress(None, 500)?;

    // Request remaining data chunks
    let initial_data_left = data_left;
    info!("requesting remaining data chunks");
    while data_left > 0 {
        info!("requesting data chunk, {} bytes left", data_left);
        let resp = send_request_chunk(data_left)?;
        info!("chunk received");

        data_left -= resp.data_chunk.len() as u32;
        rlp_buffer.extend_from_slice(&resp.data_chunk);

        info!("updating progress");
        ui::update_progress(
            None,
            500 + ((initial_data_left - data_left) / initial_data_left * 400),
        )?;
        info!("progress updated");
    }

    info!("all data chunks received");

    // write_access_list
    let payload_length: u32 = msg.access_list.iter().try_fold(0u32, |acc, item| {
        Ok::<u32, Error>(acc + access_list_item_length(item)?)
    })?;
    info!("writing RLP access list header");
    rlp::write_header(&mut rlp_buffer, payload_length, rlp::LIST_HEADER_BYTE, None);

    info!("writing RLP access list items");
    for item in &msg.access_list {
        info!("bytes from address");
        let address_bytes = bytes_from_address(&item.address)?;
        info!("calculating address length");
        let address_length = rlp::length(&&RLPItem::Bytes(address_bytes.as_slice()));

        let storage_key_items: Vec<RLPItem<'_>> = item
            .storage_keys
            .iter()
            .map(|k| RLPItem::Bytes(k.as_slice()))
            .collect();
        info!("calculating storage keys length");
        let keys_length = rlp::length(&RLPItem::List(storage_key_items.as_slice()));
        info!("writing RLP access list item header");
        rlp::write_header(
            &mut rlp_buffer,
            address_length + keys_length,
            rlp::LIST_HEADER_BYTE,
            None,
        );
        info!("writing RLP address");
        rlp::write(&mut rlp_buffer, &RLPItem::Bytes(address_bytes.as_slice()));
        info!("writing RLP storage keys");
        rlp::write(
            &mut rlp_buffer,
            &RLPItem::List(storage_key_items.as_slice()),
        );
    }

    info!("calculating transaction digest");
    let digest = crypto::keccak_256(&rlp_buffer);
    info!("transaction digest: {:?}", digest);

    let res = sign_digest(&msg, &digest)?;

    info!("transaction signed");

    ui::end_progress()?;

    ui::show_success(
        "Done",
        "Transaction signed",
        "Continue in the app",
        Some(3200),
        None,
    )?;

    Ok(res)
}

// TODO: very similar code in sign_tx.rs, should be refactored to avoid duplication
fn check_common_fields(msg: &EthereumSignTxEip1559) -> Result<()> {
    let data_length = msg.data_length;
    let data_initial_chunk = msg.data_initial_chunk.as_deref().ok_or(Error::DataError)?;
    let to = msg.to.as_deref().ok_or(Error::DataError)?;

    if data_length > 0 {
        // TODO: proper error type: DataError("Data length provided, but no initial chunk")
        info!("Data length provided, but no initial chunk");
        if data_initial_chunk.is_empty() {
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

    if msg.chain_id == 0 {
        // TODO: proper error type: DataError("Chain ID out of bounds")
        info!("Chain ID out of bounds");
        return Err(Error::DataError);
    }

    Ok(())
}

// TODO: this function is very similar to the confirm_tx_data function in sign_tx.rs, should be refactored to avoid duplication
fn confirm_tx_data(
    msg: &EthereumSignTxEip1559,
    definitions: &Definitions,
    address_bytes: &[u8],
    maximum_fee: &str,
    fee_items: &[(&str, &str, bool)],
    data_total_len: u32,
    payment_req_verifier: Option<PaymentRequestVerifier>,
) -> Result<()> {
    let dp = Bip32Path::from_slice(&msg.address_n);
    let data_initial_chunk = msg.data_initial_chunk.as_deref().ok_or(Error::DataError)?;

    if true
        == run_staking_approver(
            &msg,
            &definitions.network(),
            address_bytes,
            maximum_fee,
            fee_items,
        )?
    {
        return Ok(());
    }

    info!("handling known contract calls");
    let (token, token_address, func_sig, recipient, value) =
        handle_known_contract_calls(msg, definitions, address_bytes)?;

    info!("recipient len is {}", recipient.len());

    info!(
        "func sig len is {}",
        func_sig.as_ref().map(|s| s.len()).unwrap_or(0)
    );
    let is_approve = func_sig.as_deref() == Some(sc_func_sig_approve().as_slice());
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
            msg.chain_id,
            &definitions.network(),
            &token.unwrap(),
            &token_address.unwrap(),
            msg.chunkify.unwrap_or(false),
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
        let is_contract_interaction = token.is_none() && data_total_len > 0;

        info!("is contract interaction: {}", is_contract_interaction);
        info!("datatotal_len: {}", data_total_len);

        if let Some(mut payment_req_verifier) = payment_req_verifier {
            info!("handling payment request flow");
            if is_contract_interaction {
                // TODO: proper error type: DataError("Payment Requests don't support contract interactions")
                info!("payment requests don't support contract interactions");
                return Err(Error::DataError);
            }

            // If a payment_req_verifier is provided, then msg.payment_req must have been set.
            if msg.payment_req.is_none() || recipient_str.is_none() {
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
                msg.payment_req.as_ref().unwrap(),
                &dp,
                maximum_fee,
                fee_items,
                msg.chain_id,
                definitions.network(),
                token.as_ref(),
                &token_address_str,
            )?;
        } else {
            if is_contract_interaction {
                require_confirm_other_data(data_initial_chunk, data_total_len)?;
            };

            require_confirm_tx(
                recipient_str.as_deref(),
                unwrap!(value),
                &dp,
                maximum_fee,
                fee_items,
                definitions.network(),
                token.as_ref(),
                !is_contract_interaction,
                msg.chunkify.unwrap_or(false),
            )?;
        };
    };

    Ok(())
}

// TODO: this function is very similar to the confirm_tx_data function in sign_tx.rs, should be refactored to avoid duplication
fn run_staking_approver<'a>(
    msg: &'a EthereumSignTxEip1559,
    network: &'a EthereumNetworkInfo,
    address_bytes: &'a [u8],
    maximum_fee: &'a str,
    fee_items: &'a [(&'a str, &'a str, bool)],
) -> Result<bool> {
    let data_initial_chunk = msg.data_initial_chunk.as_deref().ok_or(Error::DataError)?;

    if data_initial_chunk.len() < SC_FUNC_SIG_BYTES {
        return Ok(false);
    }

    let func_sig = &data_initial_chunk[..SC_FUNC_SIG_BYTES];
    let data = &data_initial_chunk[SC_FUNC_SIG_BYTES..];
    if addresses_pool()
        .iter()
        .any(|addr| addr.as_slice() == address_bytes)
    {
        if func_sig == sc_func_sig_stake().as_slice() {
            handle_staking_tx_stake(data, msg, network, address_bytes, maximum_fee, fee_items)?;
            return Ok(true);
        } else if func_sig == sc_func_sig_unstake().as_slice() {
            handle_staking_tx_unstake(data, msg, network, address_bytes, maximum_fee, fee_items)?;
            return Ok(true);
        }
    }

    if addresses_accounting()
        .iter()
        .any(|addr| addr.as_slice() == address_bytes)
    {
        if func_sig == sc_func_sig_claim().as_slice() {
            handle_staking_tx_claim(
                data,
                msg,
                address_bytes,
                maximum_fee,
                fee_items,
                network,
            )?;
            return Ok(true);
        }
    }

    Ok(false)
}

pub fn get_total_length(msg: &EthereumSignTxEip1559, data_total: u32) -> Result<u32> {
    let mut length = 0;

    let to = msg.to.as_deref().ok_or(Error::DataError)?;
    let data_initial_chunk = msg.data_initial_chunk.as_deref().ok_or(Error::DataError)?;

    let to_bytes = bytes_from_address(to)?;

    info!("to bytes length: {}", to_bytes.len());

    let fields: Vec<RLPItem> = vec![
        RLPItem::Bytes(&msg.nonce),
        RLPItem::Bytes(&msg.gas_limit),
        RLPItem::Bytes(&to_bytes),
        RLPItem::Bytes(&msg.value),
        RLPItem::Int(msg.chain_id.into()),
        RLPItem::Bytes(&msg.max_gas_fee),
        RLPItem::Bytes(&msg.max_priority_fee),
    ];

    for field in &fields {
        length += rlp::length(field);
        info!("field length: {}", rlp::length(field));
    }

    length += rlp::header_length(data_total, Some(data_initial_chunk));
    length += data_total;

    let payload_length: u32 = msg.access_list.iter().try_fold(0u32, |acc, item| {
        Ok::<u32, Error>(acc + access_list_item_length(item)?)
    })?;
    let access_list_length = rlp::header_length(payload_length, None) + payload_length;

    length += access_list_length;

    Ok(length)
}

// TODO: this function is very similar to the handle_known_contract_calls function in sign_tx.rs, should be refactored to avoid duplication
fn handle_known_contract_calls(
    msg: &EthereumSignTxEip1559,
    definitions: &Definitions,
    address_bytes: &[u8],
) -> Result<(
    Option<EthereumTokenInfo>,
    Option<Vec<u8>>,
    Option<Vec<u8>>,
    Vec<u8>,
    Option<U256>,
)> {
    let data_initial_chunk = msg.data_initial_chunk.as_deref().ok_or(Error::DataError)?;
    let to = msg.to.as_deref().ok_or(Error::DataError)?;

    let mut token = None;
    let mut token_address = None;
    let mut recipient = Vec::from(address_bytes);

    // TODO: better implement parsing int value from bytes
    assert!(msg.value.len() <= 32);
    let mut value = Some(U256::from_big_endian(&msg.value));

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
        && msg.value.len() == 0
        && msg.data_length == 68
        && data_initial_chunk.len() == 68
        && (matches!(func_sig.as_deref(), Some(sig) if sig == sc_func_sig_transfer())
            || matches!( func_sig.as_deref(), Some(sig) if sig == &sc_func_sig_approve()))
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

        if matches!(func_sig.as_deref(), Some(sig) if sig == &sc_func_sig_approve())
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

// TODO: this function is very similar to the handle_staking_tx_stake and handle_staking_tx_claim functions in sign_tx.rs, should be refactored to avoid duplication
fn handle_staking_tx_stake(
    data: &[u8],
    msg: &EthereumSignTxEip1559,
    network: &EthereumNetworkInfo,
    address_bytes: &[u8],
    maximum_fee: &str,
    fee_items: &[(&str, &str, bool)],
) -> Result<()> {
    // stake args:
    // - arg0: uint64, source (1 for Trezor)

    if data.len() != SC_ARGUMENT_BYTES {
        // TODO: proper error type: ValueError: wrong number of arguments for stake (should be 1)
        return Err(Error::DataError);
    }

    assert!(msg.value.len() <= 32);
    let value = U256::from_big_endian(&msg.value);

    require_confirm_stake(
        address_bytes,
        value,
        &Bip32Path::from_slice(&msg.address_n),
        maximum_fee,
        fee_items,
        network,
    )?;

    Ok(())
}

// TODO: this function is very similar to the handle_staking_tx_stake and handle_staking_tx_claim functions in sign_tx.rs, should be refactored to avoid duplication
fn handle_staking_tx_unstake(
    data: &[u8],
    msg: &EthereumSignTxEip1559,
    network: &EthereumNetworkInfo,
    address_bytes: &[u8],
    maximum_fee: &str,
    fee_items: &[(&str, &str, bool)],
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

    require_confirm_unstake(
        address_bytes,
        value,
        &Bip32Path::from_slice(&msg.address_n),
        maximum_fee,
        fee_items,
        network,
    )?;

    Ok(())
}

// TODO: this function is very similar to the handle_staking_tx_stake and handle_staking_tx_unstake functions in sign_tx.rs, should be refactored to avoid duplication
fn handle_staking_tx_claim(
    data: &[u8],
    msg: &EthereumSignTxEip1559,
    staking_address: &[u8],
    maximum_fee: &str,
    fee_items: &[(&str, &str, bool)],
    network: &EthereumNetworkInfo,
) -> Result<()> {
    // claim has no args

    if data.len() != 0 {
        return Err(Error::DataError);
    }

    require_confirm_claim(
        staking_address,
        &Bip32Path::from_slice(&msg.address_n),
        maximum_fee,
        fee_items,
        network,
    )?;

    Ok(())
}

fn access_list_item_length(item: &EthereumAccessList) -> Result<u32> {
    let address_bytes = bytes_from_address(&item.address)?;
    let address_length = rlp::length(&RLPItem::Bytes(&address_bytes));

    let storage_key_items: Vec<RLPItem<'_>> = item
        .storage_keys
        .iter()
        .map(|k| RLPItem::Bytes(k.as_slice())) // use Bytes(...) if your enum variant is named that way
        .collect();

    let keys_length = rlp::length(&RLPItem::List(storage_key_items.as_slice()));

    Ok(rlp::header_length(address_length + keys_length, None) + address_length + keys_length)
}

fn sign_digest(msg: &EthereumSignTxEip1559, digest: &[u8; 32]) -> Result<EthereumTxRequest> {
    let signature =
        crypto::sign_typed_hash(&msg.address_n, digest, None, None, Some(msg.chain_id))?;

    info!("signing typed hash completed, processing signature");
    let mut req = EthereumTxRequest::default();
    req.signature_v = Some(signature[0] as u32 - 27);
    req.signature_r = Some(signature[1..33].to_vec());
    req.signature_s = Some(signature[33..].to_vec());

    Ok(req)
}

use crate::{
    common::{check_common_fields, confirm_tx_data, send_request_chunk},
    definitions::Definitions,
    helpers::{bytes_from_address, format_ethereum_amount, get_fee_items_eip1559},
    keychain::{Keychain, PATTERNS_ADDRESS, schemas_from_network},
    paths::{Bip32Path, unharden},
    payment_request::PaymentRequestVerifier,
    proto::{
        common::button_request::ButtonRequestType,
        ethereum::{SignTxEip1559, TxRequest, sign_tx_eip1559::AccessList},
    },
    rlp::{self, RLPItem},
};
#[cfg(not(test))]
use alloc::{vec, vec::Vec};
use primitive_types::U256;
#[cfg(test)]
use std::{vec, vec::Vec};
use trezor_app_sdk::{
    Error, Result, crypto, info,
    ui::{self, Property},
};

const TX_TYPE: u32 = 2;

pub fn sign_tx_eip1559(mut msg: SignTxEip1559) -> Result<TxRequest> {
    msg.to.get_or_insert_default();
    msg.data_initial_chunk.get_or_insert_default();

    assert!(msg.to.is_some());
    assert!(msg.data_initial_chunk.is_some());

    let to = msg
        .to
        .as_deref()
        .ok_or(Error::DataError("Missing 'to' field"))?;
    let data_initial_chunk = msg
        .data_initial_chunk
        .as_deref()
        .ok_or(Error::DataError("Missing 'data_initial_chunk' field"))?;

    let dp = Bip32Path::from_slice(&msg.address_n);

    let definitions = Definitions::from_encoded(
        msg.definitions
            .as_ref()
            .and_then(|d| d.encoded_network.as_ref().map(|v| v.as_slice())),
        msg.definitions
            .as_ref()
            .and_then(|d| d.encoded_token.as_ref().map(|v| v.as_slice())),
        Some(msg.chain_id),
        None,
    )?;

    let schemas = schemas_from_network(&PATTERNS_ADDRESS, definitions.slip44())?;
    let keychain = Keychain::new(schemas);

    // check
    if msg.max_gas_fee.len() + msg.gas_limit.len() > 30 {
        return Err(Error::DataError("Fee overflow"));
    }
    if msg.max_priority_fee.len() + msg.gas_limit.len() > 30 {
        return Err(Error::DataError("Fee overflow"));
    }

    check_common_fields(msg.data_length, data_initial_chunk, to, msg.chain_id)?;

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

    let fee_items_ref: Vec<Property> = fee_items
        .iter()
        .map(|(k, v, mono)| Property::new(k, v, *mono))
        .collect();

    let payment_req_verifier = if let Some(req) = &msg.payment_req {
        let slip44_id = unharden(msg.address_n[1]);
        Some(PaymentRequestVerifier::new(req, slip44_id)?)
    } else {
        None
    };

    confirm_tx_data(
        &dp,
        data_initial_chunk,
        msg.data_length,
        &msg.value,
        &to,
        msg.chain_id,
        msg.chunkify,
        &definitions,
        None,
        &address_bytes,
        &maximum_fee,
        &fee_items_ref,
        msg.payment_req.as_ref(),
        payment_req_verifier,
    )?;

    ui::init_progress(
        None,
        Some(tr!("progress__signing_transaction")),
        false,
        false,
    )?;
    ui::update_progress(None, 100)?;

    // sign
    let mut data = Vec::new();
    data.extend_from_slice(data_initial_chunk);
    let mut data_left = msg.data_length - data_initial_chunk.len() as u32;

    // Calculate total RLP length
    let total_length = get_total_length(&msg, msg.data_length)?;

    let mut rlp_buffer = Vec::new();

    rlp::write(&mut rlp_buffer, &RLPItem::Int(TX_TYPE.into()));

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
        rlp::write(&mut rlp_buffer, &RLPItem::Bytes(&data));
    } else {
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
    while data_left > 0 {
        let resp = send_request_chunk(data_left)?;

        data_left -= resp.data_chunk.len() as u32;
        rlp_buffer.extend_from_slice(&resp.data_chunk);

        ui::update_progress(
            None,
            500 + ((initial_data_left - data_left) / initial_data_left * 400),
        )?;
    }

    // write_access_list
    let payload_length: u32 = msg.access_list.iter().try_fold(0u32, |acc, item| {
        Ok::<u32, Error>(acc + access_list_item_length(item)?)
    })?;
    rlp::write_header(&mut rlp_buffer, payload_length, rlp::LIST_HEADER_BYTE, None);

    for item in &msg.access_list {
        let address_bytes = bytes_from_address(&item.address)?;
        let address_length = rlp::length(&&RLPItem::Bytes(address_bytes.as_slice()));
        let storage_key_items: Vec<RLPItem<'_>> = item
            .storage_keys
            .iter()
            .map(|k| RLPItem::Bytes(k.as_slice()))
            .collect();
        let keys_length = rlp::length(&RLPItem::List(storage_key_items.as_slice()));
        rlp::write_header(
            &mut rlp_buffer,
            address_length + keys_length,
            rlp::LIST_HEADER_BYTE,
            None,
        );
        rlp::write(&mut rlp_buffer, &RLPItem::Bytes(address_bytes.as_slice()));
        rlp::write(
            &mut rlp_buffer,
            &RLPItem::List(storage_key_items.as_slice()),
        );
    }

    let digest = crypto::keccak_256(&rlp_buffer);
    let res = sign_digest(&msg, &digest)?;

    ui::end_progress()?;

    ui::show_success(
        tr!("words__title_done"),
        tr!("send__transaction_signed"),
        tr!("instructions__continue_in_app"),
        Some(3200),
        None,
        ButtonRequestType::ButtonRequestOther.into(),
    )?;

    Ok(res)
}

pub fn get_total_length(msg: &SignTxEip1559, data_total: u32) -> Result<u32> {
    let mut length = 0;

    let to = msg
        .to
        .as_deref()
        .ok_or(Error::DataError("Missing 'to' field"))?;
    let data_initial_chunk = msg
        .data_initial_chunk
        .as_deref()
        .ok_or(Error::DataError("Missing 'data_initial_chunk' field"))?;

    let to_bytes = bytes_from_address(to)?;

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

fn access_list_item_length(item: &AccessList) -> Result<u32> {
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

fn sign_digest(msg: &SignTxEip1559, digest: &[u8; 32]) -> Result<TxRequest> {
    let signature =
        crypto::sign_typed_hash(&msg.address_n, digest, None, None, Some(msg.chain_id))?;

    let mut req = TxRequest::default();
    req.signature_v = Some(signature[0] as u32 - 27);
    req.signature_r = Some(signature[1..33].to_vec());
    req.signature_s = Some(signature[33..].to_vec());

    Ok(req)
}

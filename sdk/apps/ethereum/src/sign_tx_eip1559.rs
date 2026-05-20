use crate::{
    alloc_types::{Vec, vec},
    common::{
        check_common_fields, confirm_data_and_summary, confirm_tx_data, request_initial_data,
    },
    definitions::Definitions,
    helpers::{bytes_from_address, format_ethereum_amount, get_fee_items_eip1559},
    paths::{Bip32Path, unharden},
    payment_request::PaymentRequestVerifier,
    proto::{
        common::button_request::ButtonRequestType,
        ethereum::{SignTxEip1559, TxRequest, sign_tx_eip1559::AccessList},
    },
    rlp::{self, RLPItem},
};
use primitive_types::U256;
use trezor_app_sdk::{
    Error, Result, crypto,
    ui::{self, Property},
    unwrap,
};

const TX_TYPE: u32 = 2;

pub fn sign_tx_eip1559(mut msg: SignTxEip1559) -> Result<TxRequest> {
    msg.to.get_or_insert_default();
    msg.data_initial_chunk.get_or_insert_default();

    assert!(msg.to.is_some());
    assert!(msg.data_initial_chunk.is_some());

    let to = unwrap!(msg.to.as_deref());
    let data_initial_chunk = unwrap!(msg.data_initial_chunk.as_deref());

    let dp = Bip32Path::from_slice(&msg.address_n);

    let encoded_network = msg
        .definitions
        .as_ref()
        .and_then(|d| d.encoded_network.as_deref());

    let encoded_token = msg
        .definitions
        .as_ref()
        .and_then(|d| d.encoded_token.as_deref());

    let definitions =
        Definitions::from_encoded(encoded_network, encoded_token, Some(msg.chain_id), None)?;

    // check
    if msg.max_gas_fee.len() + msg.gas_limit.len() > 30 {
        return Err(Error::DataError("Fee overflow"));
    }
    if msg.max_priority_fee.len() + msg.gas_limit.len() > 30 {
        return Err(Error::DataError("Fee overflow"));
    }

    check_common_fields(msg.data_length, data_initial_chunk, to, msg.chain_id)?;

    // have a user confirm signing
    crypto::verify_derivation_path(
        dp.as_slice(),
        encoded_network,
        encoded_token,
        Some(msg.chain_id),
    )?;

    let sender_bytes = crypto::get_eth_pubkey_hash(
        dp.as_slice(),
        encoded_network,
        encoded_token,
        Some(msg.chain_id),
    )?;

    let address_bytes = bytes_from_address(to)?;
    let max_gas_fee = U256::from_big_endian(&msg.max_gas_fee);
    let max_priority_fee = U256::from_big_endian(&msg.max_priority_fee);
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

    let mut hasher = crypto::Keccak256::new(None);

    rlp::write(&mut hasher, &RLPItem::Int(TX_TYPE.into()));

    rlp::write_header(
        &mut hasher,
        get_digest_length(&msg, msg.data_length)?,
        rlp::LIST_HEADER_BYTE,
        None,
    );

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
        rlp::write(&mut hasher, field);
    }

    let initial_data =
        request_initial_data(&mut hasher, msg.data_length as usize, data_initial_chunk)?;

    let (confirm_data_chunk, confirm_summary) = confirm_tx_data(
        &initial_data,
        msg.data_length as usize,
        data_initial_chunk,
        msg.value.as_ref(),
        to,
        &dp,
        &definitions,
        None,
        &address_bytes,
        &maximum_fee,
        &fee_items_ref,
        payment_req_verifier,
        &sender_bytes,
        msg.chunkify,
        msg.payment_req.as_ref(),
        msg.chain_id,
        msg.definitions.as_ref(),
    )?;

    confirm_data_and_summary(
        confirm_data_chunk,
        confirm_summary,
        &initial_data,
        msg.data_length as usize,
        &mut hasher,
    )?;

    // write_access_list
    let payload_length: u32 = msg.access_list.iter().try_fold(0u32, |acc, item| {
        Ok::<u32, Error>(acc + access_list_item_length(item)?)
    })?;
    rlp::write_header(&mut hasher, payload_length, rlp::LIST_HEADER_BYTE, None);

    for item in &msg.access_list {
        let address_bytes = bytes_from_address(&item.address)?;
        let address_length = rlp::length(&RLPItem::Bytes(address_bytes.as_slice()));
        let storage_key_items: Vec<RLPItem<'_>> = item
            .storage_keys
            .iter()
            .map(|k| RLPItem::Bytes(k.as_slice()))
            .collect();
        let keys_length = rlp::length(&RLPItem::List(storage_key_items.as_slice()));
        rlp::write_header(
            &mut hasher,
            address_length + keys_length,
            rlp::LIST_HEADER_BYTE,
            None,
        );
        rlp::write(&mut hasher, &RLPItem::Bytes(address_bytes.as_slice()));
        rlp::write(&mut hasher, &RLPItem::List(storage_key_items.as_slice()));
    }

    let digest = hasher.digest();
    let res = sign_digest(&msg, &digest)?;

    ui::end_progress()?;

    ui::show_success(
        tr!("words__title_done"),
        tr!("send__transaction_signed"),
        tr!("instructions__continue_in_app"),
        Some(3200),
        None,
        ButtonRequestType::Other.into(),
    )?;

    Ok(res)
}

pub fn get_digest_length(msg: &SignTxEip1559, data_total: u32) -> Result<u32> {
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
        crypto::sign_typed_hash(&msg.address_n, digest, None, None, Some(msg.chain_id), true)?;

    let req = TxRequest {
        signature_v: Some(signature[0] as u32 - 27),
        signature_r: Some(signature[1..33].to_vec()),
        signature_s: Some(signature[33..].to_vec()),
        ..Default::default()
    };

    Ok(req)
}

use crate::{
    common::{
        EIP_7702_TX_TYPE, SC_ARGUMENT_ADDRESS_BYTES, SC_ARGUMENT_BYTES, check_common_fields,
        confirm_tx_data, get_eip_7702_known_address, send_request_chunk,
    },
    definitions::Definitions,
    helpers::{bytes_from_address, format_ethereum_amount, get_fee_items_regular},
    keychain::{Keychain, PATTERNS_ADDRESS, schemas_from_network},
    paths::{Bip32Path, unharden},
    payment_request::PaymentRequestVerifier,
    proto::{
        common::button_request::ButtonRequestType,
        ethereum::{EthereumSignTx, EthereumTxRequest},
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

// Compile-time assertion
const _: () = assert!(SC_ARGUMENT_ADDRESS_BYTES <= SC_ARGUMENT_BYTES);

// Maximum chain_id which returns the full signature_v (which must fit into an uint32).
// chain_ids larger than this will only return one bit and the caller must recalculate
// the full value: v = 2 * chain_id + 35 + v_bit
const MAX_CHAIN_ID: u64 = (0xFFFF_FFFF - 36) / 2;

pub fn sign_tx(mut msg: EthereumSignTx) -> Result<EthereumTxRequest> {
    msg.nonce.get_or_insert_default();
    msg.to.get_or_insert_default();
    msg.value.get_or_insert_default();
    msg.data_initial_chunk.get_or_insert_default();
    msg.data_length.get_or_insert_default();

    assert!(msg.nonce.is_some());
    assert!(msg.to.is_some());
    assert!(msg.value.is_some());
    assert!(msg.data_initial_chunk.is_some());
    assert!(msg.data_length.is_some());

    let nonce = msg.nonce.as_deref().ok_or(Error::DataError)?;
    let to = msg.to.as_deref().ok_or(Error::DataError)?;
    let value = msg.value.as_deref().ok_or(Error::DataError)?;
    let data_initial_chunk = msg.data_initial_chunk.as_deref().ok_or(Error::DataError)?;
    let data_total = msg.data_length.ok_or(Error::DataError)?;

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

    info!("checking common fields");

    check_common_fields(data_total, data_initial_chunk, to, msg.chain_id)?;

    info!("getting bytes from address");

    let address_bytes = bytes_from_address(to)?;

    info!("checking transaction type");

    if !matches!(
        msg.tx_type,
        Some(1) | Some(6) | Some(EIP_7702_TX_TYPE) | None
    ) {
        info!("unsupported transaction type");
        return Err(Error::DataError);
    }

    if matches!(msg.tx_type, Some(EIP_7702_TX_TYPE)) {
        // TODO: safety checks
        // if safety_checks.is_strict():
        // raise DataError("EIP-7702 not allowed in strict checks")

        if get_eip_7702_known_address(&address_bytes).is_none() {
            // TODO: proper error type: DataError("Unknown EIP-7702 address")
            info!("Unknown EIP-7702 address");
            return Err(Error::DataError);
        }
    }

    if msg.gas_price.len() + msg.gas_limit.len() > 30 {
        // TODO: proper error type: DataError("Fee overflow")
        info!("Fee overflow");
        return Err(Error::DataError);
    }

    info!("validating path");
    // have the user confirm signing
    dp.validate(&keychain)?;

    info!("parsing fee information");

    info!("gas price");

    // TODO: better implement parsing int value from bytes
    assert!(msg.gas_price.len() <= 32);
    let gas_price = U256::from_big_endian(&msg.gas_price);

    info!("gas limit");
    // TODO: better implement parsing int value from bytes
    assert!(msg.gas_limit.len() <= 32);
    let gas_limit = U256::from_big_endian(&msg.gas_limit);

    info!("max fee");
    let maximum_fee =
        format_ethereum_amount(gas_price * gas_limit, None, &definitions.network(), false);
    let fee_items = get_fee_items_regular(gas_price, gas_limit, &definitions.network());

    let fee_items_ref: Vec<Property> = fee_items
        .iter()
        .map(|(k, v, mono)| Property::new(k, v, *mono))
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
        &dp,
        data_initial_chunk,
        data_total,
        value,
        &to,
        msg.chain_id,
        msg.chunkify,
        &definitions,
        msg.tx_type,
        &address_bytes,
        &maximum_fee,
        &fee_items_ref,
        msg.payment_req.as_ref(),
        payment_req_verifier,
    )?;

    ui::init_progress(None, Some("Signing transaction..."), false, false)?;
    ui::update_progress(None, 100)?;

    // sign
    let mut data = Vec::new();
    data.extend_from_slice(data_initial_chunk);
    let mut data_left = data_total - data_initial_chunk.len() as u32;

    // Calculate total RLP length
    let total_length = get_total_length(&msg, data_total)?;
    info!("total RLP length: {}", total_length);

    let mut rlp_buffer = Vec::new();

    info!("writing RLP header");
    rlp::write_header(&mut rlp_buffer, total_length, rlp::LIST_HEADER_BYTE, None);

    info!("current len of RLP buffer: {}", rlp_buffer.len());

    if let Some(tx_type) = msg.tx_type {
        rlp::write(&mut rlp_buffer, &RLPItem::Int(tx_type.into()));
    }

    // Write transaction fields
    let fields: Vec<RLPItem> = vec![
        RLPItem::Bytes(nonce),
        RLPItem::Bytes(&msg.gas_price),
        RLPItem::Bytes(&msg.gas_limit),
        RLPItem::Bytes(&address_bytes),
        RLPItem::Bytes(value),
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
            data_total,
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

    info!("all data chunks received, finalizing RLP encoding");
    // EIP-155 replay protection
    rlp::write(&mut rlp_buffer, &RLPItem::Int(msg.chain_id.into()));
    rlp::write(&mut rlp_buffer, &RLPItem::Int(0.into()));
    rlp::write(&mut rlp_buffer, &RLPItem::Int(0.into()));
    info!("RLP encoding finalized, total length: {}", rlp_buffer.len());

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
        ButtonRequestType::ButtonRequestOther.into(),
    )?;

    Ok(res)
}

fn sign_digest(msg: &EthereumSignTx, digest: &[u8; 32]) -> Result<EthereumTxRequest> {
    let (encoded_network, encoded_token) = match &msg.definitions {
        Some(def) => (
            def.encoded_network.as_ref().map(|d| d.as_ref()),
            def.encoded_token.as_ref().map(|d| d.as_ref()),
        ),
        None => (None, None),
    };
    info!("signing typed hash");

    let signature = crypto::sign_typed_hash(
        &msg.address_n,
        digest,
        encoded_network,
        encoded_token,
        Some(msg.chain_id),
    )?;

    info!("signing typed hash completed, processing signature");
    let mut req = EthereumTxRequest::default();
    let mut signature_v: u32 = signature[0].into();

    if msg.chain_id > MAX_CHAIN_ID {
        signature_v -= 27;
    } else {
        signature_v += 2 * msg.chain_id as u32 + 8;
    }

    req.signature_v = Some(signature_v);
    req.signature_r = Some(signature[1..33].to_vec());
    req.signature_s = Some(signature[33..].to_vec());

    Ok(req)
}

pub fn get_total_length(msg: &EthereumSignTx, data_total: u32) -> Result<u32> {
    let mut length = 0;

    if let Some(tx_type) = msg.tx_type {
        length += rlp::length(&RLPItem::Int(tx_type.into()));
        info!(
            "tx_type length: {:?}",
            rlp::length(&RLPItem::Int(tx_type.into()))
        );
    }

    let nonce = msg.nonce.as_deref().ok_or(Error::DataError)?;
    let value = msg.value.as_deref().ok_or(Error::DataError)?;
    let to_str = msg.to.as_deref().ok_or(Error::DataError)?;
    let data_initial_chunk = msg.data_initial_chunk.as_deref().ok_or(Error::DataError)?;

    let to_bytes = bytes_from_address(to_str)?;

    info!("to bytes length: {}", to_bytes.len());

    let fields: Vec<RLPItem> = vec![
        RLPItem::Bytes(nonce),
        RLPItem::Bytes(&msg.gas_price),
        RLPItem::Bytes(&msg.gas_limit),
        RLPItem::Bytes(&to_bytes),
        RLPItem::Bytes(value),
        RLPItem::Int(msg.chain_id.into()),
        RLPItem::Int(0.into()),
        RLPItem::Int(0.into()),
    ];

    for field in &fields {
        length += rlp::length(field);
        info!("field length: {}", rlp::length(field));
    }

    length += rlp::header_length(data_total, Some(data_initial_chunk));
    length += data_total;

    Ok(length)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::strutil::hex_decode;

    #[test]
    fn test_eip7702_known_address_constants() {
        assert_eq!(
            &ADDR_EIP7702_UNISWAP[..],
            hex_decode("000000009B1D0aF20D8C6d0A44e162d11F9b8f00")
                .unwrap()
                .as_slice()
        );
        assert_eq!(
            &ADDR_EIP7702_ALCHEMY[..],
            hex_decode("69007702764179f14F51cdce752f4f775d74E139")
                .unwrap()
                .as_slice()
        );
        assert_eq!(
            &ADDR_EIP7702_AMBIRE[..],
            hex_decode("5A7FC11397E9a8AD41BF10bf13F22B0a63f96f6d")
                .unwrap()
                .as_slice()
        );
        assert_eq!(
            &ADDR_EIP7702_METAMASK[..],
            hex_decode("63c0c19a282a1b52b07dd5a65b58948a07dae32b")
                .unwrap()
                .as_slice()
        );
        assert_eq!(
            &ADDR_EIP7702_EF_AA[..],
            hex_decode("4Cd241E8d1510e30b2076397afc7508Ae59C66c9")
                .unwrap()
                .as_slice()
        );
        assert_eq!(
            &ADDR_EIP7702_LUGANODES[..],
            hex_decode("17c11FDdADac2b341F2455aFe988fec4c3ba26e3")
                .unwrap()
                .as_slice()
        );
    }
}

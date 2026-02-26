use crate::{
    definitions::Definitions,
    helpers::{Property, bytes_from_address, format_ethereum_amount, get_fee_items_regular},
    keychain::{Keychain, PATTERNS_ADDRESS, schemas_from_network},
    paths::Bip32Path,
    proto::ethereum::{EthereumSignTx, EthereumTxAck, EthereumTxRequest},
    rlp::{self, RLPItem},
    strutil::hex_decode,
};
#[cfg(not(test))]
use alloc::{collections::BTreeMap, vec, vec::Vec};
#[cfg(test)]
use std::{collections::BTreeMap, vec, vec::Vec};
use trezor_app_sdk::{Error, Result, crypto};

// EIP-7702
const EIP_7702_TX_TYPE: u32 = 4;

// Maximum chain_id which returns the full signature_v (which must fit into an uint32).
// chain_ids larger than this will only return one bit and the caller must recalculate
// the full value: v = 2 * chain_id + 35 + v_bit
const MAX_CHAIN_ID: u64 = (0xFFFF_FFFF - 36) / 2;

pub fn get_eip_7702_known_addresses() -> BTreeMap<Vec<u8>, &'static str> {
    let mut map = BTreeMap::new();
    map.insert(
        hex_decode("000000009B1D0aF20D8C6d0A44e162d11F9b8f00").unwrap(),
        "Uniswap",
    );
    map.insert(
        hex_decode("69007702764179f14F51cdce752f4f775d74E139").unwrap(),
        "alchemyplatform",
    );
    map.insert(
        hex_decode("5A7FC11397E9a8AD41BF10bf13F22B0a63f96f6d").unwrap(),
        "AmbireTech",
    );
    map.insert(
        hex_decode("63c0c19a282a1b52b07dd5a65b58948a07dae32b").unwrap(),
        "MetaMask",
    );
    map.insert(
        hex_decode("4Cd241E8d1510e30b2076397afc7508Ae59C66c9").unwrap(),
        "Ethereum Foundation AA team",
    );
    map.insert(
        hex_decode("17c11FDdADac2b341F2455aFe988fec4c3ba26e3").unwrap(),
        "Luganodes",
    );
    map
}

pub fn sign_tx(msg: EthereumSignTx) -> Result<EthereumTxRequest> {
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
    )
    .unwrap();

    let schemas = schemas_from_network(&PATTERNS_ADDRESS, definitions.slip44())?;
    let keychain = Keychain::new(schemas);

    let data_total = msg.data_length.unwrap_or(0);

    check_common_fields(&msg)?;

    // TODO: Implement Ethereum transaction signing

    let to = msg.to.as_ref().map(|s| s.as_str()).unwrap_or("");
    let address_bytes = bytes_from_address(to)?;

    if !matches!(
        msg.tx_type,
        Some(1) | Some(6) | Some(EIP_7702_TX_TYPE) | None
    ) {
        // TODO: DataError("tx_type out of bounds")
        return Err(Error::DataError);
    }

    if matches!(msg.tx_type, Some(EIP_7702_TX_TYPE)) {
        // TODO: safety checks
        // if safety_checks.is_strict():
        // raise DataError("EIP-7702 not allowed in strict checks")

        if !get_eip_7702_known_addresses().contains_key(&address_bytes) {
            // TODO DataError("Unknown EIP-7702 address")
            return Err(Error::DataError);
        }
    }

    if msg.gas_price.len() + msg.gas_limit.len() > 30 {
        // TODO DataError("Fee overflow")
        return Err(Error::DataError);
    }

    // have the user confirm signing
    dp.validate(&keychain)?;

    let mut buf = [0u8; 16];
    buf[16 - msg.gas_price.len()..].copy_from_slice(&msg.gas_price);
    let gas_price = u128::from_be_bytes(buf);

    let mut buf = [0u8; 16];
    buf[16 - msg.gas_limit.len()..].copy_from_slice(&msg.gas_limit);
    let gas_limit = u128::from_be_bytes(buf);

    let maximum_fee =
        format_ethereum_amount(gas_price * gas_limit, None, &definitions.network(), false);
    let fee_items = get_fee_items_regular(gas_price, gas_limit, &definitions.network());

    let payment_request_verifier: Option<u32> = if let Some(req) = &msg.payment_req {
        // TODO implement
        // slip44_id = paths.unharden(msg.address_n[1])
        // payment_req_verifier = PaymentRequestVerifier(
        //     msg.payment_req,
        //     slip44_id,
        //     keychain,
        //     amount_size_bytes=32,
        // )
        None
    } else {
        None
    };

    confirm_tx_data(
        &msg,
        &definitions,
        msg.tx_type,
        &address_bytes,
        &maximum_fee,
        &fee_items,
        data_total,
    )?;

    // TODO progress

    // sign
    let mut data = Vec::new();
    if let Some(initial_chunk) = &msg.data_initial_chunk {
        data.extend_from_slice(initial_chunk);
    }
    let mut data_left = data_total - data.len() as u32;

    // Calculate total RLP length
    let total_length = get_total_length(&msg, data_total);

    let mut rlp_buffer = Vec::new();

    rlp::write_header(&mut rlp_buffer, total_length, rlp::LIST_HEADER_BYTE, None);

    if let Some(tx_type) = msg.tx_type {
        rlp::write(&mut rlp_buffer, &RLPItem::Int(tx_type as u64));
    }

    // Write transaction fields
    let nonce = msg.nonce.as_ref().map(|v| v.as_slice()).unwrap_or(&[]);
    let value = msg.value.as_ref().map(|v| v.as_slice()).unwrap_or(&[]);

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
        rlp::write(&mut rlp_buffer, &RLPItem::Bytes(&data));
    } else {
        rlp::write_header(
            &mut rlp_buffer,
            data_total,
            rlp::STRING_HEADER_BYTE,
            Some(&data),
        );
        rlp_buffer.extend_from_slice(&data);
    }

    // TODO: Report progress (500)
    // progress_obj.report(500);

    // Request remaining data chunks
    let initial_data_left = data_left;
    while data_left > 0 {
        let resp = send_request_chunk(data_left)?;

        data_left -= resp.data_chunk.len() as u32;
        rlp_buffer.extend_from_slice(&resp.data_chunk);

        // TODO: Report progress
        // let progress = 500 + ((initial_data_left - data_left) * 400 / initial_data_left);
        // progress_obj.report(progress);
    }

    // EIP-155 replay protection
    rlp::write(&mut rlp_buffer, &RLPItem::Int(msg.chain_id));
    rlp::write(&mut rlp_buffer, &RLPItem::Int(0));
    rlp::write(&mut rlp_buffer, &RLPItem::Int(0));

    let digest = crypto::keccak_256(&data);

    let res = sign_digest(&msg, &digest)?;

    // TODO progress stop, show continue in the app

    Ok(res)
}

fn check_common_fields(msg: &EthereumSignTx) -> Result<()> {
    let data_length = msg.data_length.unwrap_or(0);

    if data_length > 0 {
        if msg.data_initial_chunk.is_none() {
            // DataError("Data length provided, but no initial chunk")
            return Err(Error::DataError);
        }
    }

    // Our encoding only supports transactions up to 2^24 bytes. To
    // prevent exceeding the limit we use a stricter limit on data length.
    if data_length > 16_000_000 {
        // DataError("Data length exceeds limit")
        return Err(Error::DataError);
    }

    if let Some(data_initial_chunk) = &msg.data_initial_chunk {
        if data_initial_chunk.len() > data_length as usize {
            // DataError("Invalid size of initial chunk")
            return Err(Error::DataError);
        }
    }

    let to_len = msg.to.as_ref().map(|s| s.len()).unwrap_or(0);
    if !matches!(to_len, 0 | 40 | 42) {
        // DataError("Invalid recipient address")
        return Err(Error::DataError);
    }

    if msg.to.is_none() && matches!(msg.data_length, Some(0)) {
        // sending transaction to address 0 (contract creation) without a data field
        // DataError("Contract creation without data")
        return Err(Error::DataError);
    }

    if msg.chain_id == 0 {
        // DataError("Chain ID out of bounds")
        return Err(Error::DataError);
    }

    Ok(())
}

fn confirm_tx_data(
    _msg: &EthereumSignTx,
    _definitions: &Definitions,
    _tx_type: Option<u32>,
    _address_bytes: &[u8],
    _maximum_fee: &str,
    _fee_items: &[Property],
    _data_total_len: u32,
) -> Result<()> {
    // TODO implement
    Ok(())
}

fn sign_digest(msg: &EthereumSignTx, digest: &[u8]) -> Result<EthereumTxRequest> {
    let (encoded_network, encoded_token) = match &msg.definitions {
        Some(def) => (
            def.encoded_network.as_ref().map(|d| d.as_ref()),
            def.encoded_token.as_ref().map(|d| d.as_ref()),
        ),
        None => (None, None),
    };

    let signature =
        crypto::sign_typed_hash(&msg.address_n, digest, encoded_network, encoded_token)?;

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

fn send_request_chunk(_data_left: u32) -> Result<EthereumTxAck> {
    // use trezor_app_sdk::message::{send_message, receive_message};

    // let mut req = EthereumTxRequest::default();
    // req.data_length = Some(core::cmp::min(data_left, 1024) as u32);

    // send_message(req)?;
    // let resp: EthereumTxAck = receive_message().await?;

    let resp = EthereumTxAck::default(); // TODO Placeholder for actual implementation

    Ok(resp)
}

pub fn get_total_length(msg: &EthereumSignTx, data_total: u32) -> u32 {
    let mut length = 0;

    if let Some(tx_type) = msg.tx_type {
        length += rlp::length(&RLPItem::Int(tx_type as u64));
    }

    let nonce = msg.nonce.as_ref().map(|v| v.as_slice()).unwrap_or(&[]);
    let value = msg.value.as_ref().map(|v| v.as_slice()).unwrap_or(&[]);
    let to_bytes = msg.to.as_ref().map(|s| s.as_bytes()).unwrap_or(&[]);

    let fields: Vec<RLPItem> = vec![
        RLPItem::Bytes(nonce),
        RLPItem::Bytes(&msg.gas_price),
        RLPItem::Bytes(&msg.gas_limit),
        RLPItem::Bytes(to_bytes),
        RLPItem::Bytes(value),
        RLPItem::Int(msg.chain_id),
        RLPItem::Int(0),
        RLPItem::Int(0),
    ];

    for field in &fields {
        length += rlp::length(field);
    }

    length += rlp::header_length(
        data_total,
        msg.data_initial_chunk.as_ref().map(|v| v.as_slice()),
    );
    length += data_total;

    length
}

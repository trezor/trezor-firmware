use crate::{
    alloc_types::{Vec, vec},
    common::{
        EIP_7702_TX_TYPE, check_common_fields, confirm_data_and_summary, confirm_tx_data,
        get_eip_7702_known_address, get_eth_pubkey_hash, request_initial_data,
    },
    definitions::Definitions,
    helpers::{bytes_from_address, format_ethereum_amount, get_fee_items_regular},
    paths::{Bip32Path, unharden},
    payment_request::PaymentRequestVerifier,
    proto::{
        common::button_request::ButtonRequestType,
        ethereum::{SignTx, TxRequest},
    },
    rlp::{self, RLPItem},
};
use primitive_types::U256;
use trezor_app_sdk::{
    Error, Result, ResultExt, crypto,
    ui::{self, Property},
};

// Maximum chain_id which returns the full signature_v (which must fit into an uint32).
// chain_ids larger than this will only return one bit and the caller must recalculate
// the full value: v = 2 * chain_id + 35 + v_bit
const MAX_CHAIN_ID: u64 = (0xFFFF_FFFF - 36) / 2;

pub fn sign_tx(mut msg: SignTx) -> Result<TxRequest> {
    msg.nonce.get_or_insert_default();
    msg.to.get_or_insert_default();
    msg.value.get_or_insert_default();
    msg.data_initial_chunk.get_or_insert_default();
    msg.data_length.get_or_insert_default();

    let nonce = msg
        .nonce
        .as_deref()
        .ok_or(Error::DataError("Missing nonce"))?;
    let to = msg
        .to
        .as_deref()
        .ok_or(Error::DataError("Missing to address"))?;
    let value = msg
        .value
        .as_deref()
        .ok_or(Error::DataError("Missing value"))?;
    let data_initial_chunk = msg
        .data_initial_chunk
        .as_deref()
        .ok_or(Error::DataError("Missing data initial chunk"))?;
    let data_length = msg
        .data_length
        .ok_or(Error::DataError("Missing data length"))?;

    let dp = Bip32Path::from_slice(&msg.address_n);

    let (encoded_network, encoded_token) = match &msg.definitions {
        Some(def) => (def.encoded_network.as_deref(), def.encoded_token.as_deref()),
        None => (None, None),
    };

    let definitions =
        Definitions::from_encoded(encoded_network, encoded_token, Some(msg.chain_id), None)
            .context("Failed to decode definitions")?;

    check_common_fields(data_length, data_initial_chunk, to, msg.chain_id)
        .context("Failed to check common fields")?;

    let address_bytes = bytes_from_address(to).context("Failed to convert address to bytes")?;

    let valid_tx_types = [Some(1), Some(6), Some(EIP_7702_TX_TYPE), None];

    if !valid_tx_types.contains(&msg.tx_type) {
        return Err(Error::DataError("tx_type out of bounds"));
    }

    if matches!(msg.tx_type, Some(EIP_7702_TX_TYPE)) {
        // TODO: safety checks
        // if safety_checks.is_strict():
        // raise DataError("EIP-7702 not allowed in strict checks")

        if get_eip_7702_known_address(&address_bytes).is_none() {
            return Err(Error::DataError("Unknown EIP-7702 address"));
        }
    }

    if msg.gas_price.len() + msg.gas_limit.len() > 30 {
        return Err(Error::DataError("Fee overflow"));
    }

    // have the user confirm signing
    crypto::verify_derivation_path(
        dp.as_slice(),
        encoded_network,
        encoded_token,
        Some(msg.chain_id),
    )
    .context("Failed to verify derivation path")?;

    let sender_bytes = get_eth_pubkey_hash(&dp).context("Failed to get eth pubkey hash")?;

    let gas_price = U256::from_big_endian(&msg.gas_price);
    let gas_limit = U256::from_big_endian(&msg.gas_limit);
    let maximum_fee =
        format_ethereum_amount(gas_price * gas_limit, None, definitions.network(), false)
            .context("Failed to create max fee string")?;
    let fee_items = get_fee_items_regular(gas_price, gas_limit, definitions.network())
        .context("Failed to create fee items")?;
    let fee_items_ref: Vec<Property> = fee_items
        .iter()
        .map(|(k, v, mono)| Property::new(k, v, *mono))
        .collect();

    let payment_req_verifier = if let Some(req) = &msg.payment_req {
        let slip44_id = unharden(dp.as_slice()[1]);
        Some(PaymentRequestVerifier::new(req, slip44_id)?)
    } else {
        None
    };

    let mut hasher = crypto::Keccak256::new(None);
    rlp::write_header(
        &mut hasher,
        get_total_length(
            nonce,
            &msg.gas_price,
            &msg.gas_limit,
            to,
            value,
            data_initial_chunk,
            data_length,
            msg.chain_id,
            msg.tx_type,
        )?,
        rlp::LIST_HEADER_BYTE,
        None,
    );

    if let Some(tx_type) = msg.tx_type {
        rlp::write(&mut hasher, &RLPItem::Int(tx_type.into()));
    }

    // Write transaction fields
    let fields = [
        RLPItem::Bytes(nonce),
        RLPItem::Bytes(&msg.gas_price),
        RLPItem::Bytes(&msg.gas_limit),
        RLPItem::Bytes(&address_bytes),
        RLPItem::Bytes(value),
    ];

    for field in &fields {
        rlp::write(&mut hasher, field);
    }

    let initial_data = request_initial_data(&mut hasher, data_length as usize, data_initial_chunk)
        .context("Failed to request initial data")?;

    let (confirm_data_chunk, confirm_summary) = confirm_tx_data(
        &initial_data,
        data_length as usize,
        data_initial_chunk,
        value,
        to,
        &dp,
        &definitions,
        msg.tx_type,
        &address_bytes,
        &maximum_fee,
        &fee_items_ref,
        payment_req_verifier,
        &sender_bytes,
        msg.chunkify,
        msg.payment_req.as_ref(),
        msg.chain_id,
        msg.definitions.as_ref(),
        msg.supports_definition_request,
    )
    .context("Failed to confirm transaction data")?;

    confirm_data_and_summary(
        confirm_data_chunk,
        confirm_summary,
        &initial_data,
        data_length as usize,
        &mut hasher,
    )
    .context("Failed to confirm data and summary")?;

    // EIP-155 replay protection
    let fields = [
        RLPItem::Int(msg.chain_id.into()),
        RLPItem::Int(0.into()),
        RLPItem::Int(0.into()),
    ];
    for field in &fields {
        rlp::write(&mut hasher, field);
    }

    let digest = hasher.digest();

    // transaction data confirmed, proceed with signing
    let res = sign_digest(&msg, &digest).context("Failed to sign digest")?;
    ui::show_success(ui::ShowSuccess::new(
        tr!("words__title_done"),
        tr!("send__transaction_signed"),
        tr!("instructions__continue_in_app"),
        Some(3200),
        None,
        ButtonRequestType::Other.into(),
    ))?;

    Ok(res)
}

fn sign_digest(msg: &SignTx, digest: &[u8; 32]) -> Result<TxRequest> {
    let (encoded_network, encoded_token) = match &msg.definitions {
        Some(def) => (
            def.encoded_network.as_ref().map(|d| d.as_ref()),
            def.encoded_token.as_ref().map(|d| d.as_ref()),
        ),
        None => (None, None),
    };

    let signature = crypto::sign_typed_hash(
        &msg.address_n,
        digest,
        encoded_network,
        encoded_token,
        Some(msg.chain_id),
        true,
    )
    .context("Failed to sign typed hash")?;

    let mut req = TxRequest::default();
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

pub fn get_total_length(
    nonce: &[u8],
    gas_price: &[u8],
    gas_limit: &[u8],
    to: &str,
    value: &[u8],
    data_initial_chunk: &[u8],
    data_length: u32,
    chain_id: u64,
    tx_type: Option<u32>,
) -> Result<u32> {
    let mut length = 0;

    if let Some(tx_type) = tx_type {
        length += rlp::length(&RLPItem::Int(tx_type.into()));
    }

    let to_bytes = bytes_from_address(to).context("Failed to convert address to bytes")?;

    let fields: Vec<RLPItem> = vec![
        RLPItem::Bytes(nonce),
        RLPItem::Bytes(gas_price),
        RLPItem::Bytes(gas_limit),
        RLPItem::Bytes(&to_bytes),
        RLPItem::Bytes(value),
        RLPItem::Int(chain_id.into()),
        RLPItem::Int(0.into()),
        RLPItem::Int(0.into()),
    ];

    for field in &fields {
        length += rlp::length(field);
    }

    length += rlp::header_length(data_length, Some(data_initial_chunk));
    length += data_length;

    Ok(length)
}

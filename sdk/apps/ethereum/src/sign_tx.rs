use crate::{
    common::{
        SC_ARGUMENT_ADDRESS_BYTES, SC_ARGUMENT_BYTES, SC_FUNC_APPROVE_REVOKE_AMOUNT,
        SC_FUNC_SIG_APPROVE, SC_FUNC_SIG_BYTES, SC_FUNC_SIG_TRANSFER, require_confirm_address,
        require_confirm_approve, require_confirm_other_data, require_confirm_payment_request,
        require_confirm_tx, run_staking_approver, send_request_chunk,
    },
    definitions::Definitions,
    helpers::{
        address_from_bytes, bytes_from_address, format_ethereum_amount, get_fee_items_regular,
    },
    keychain::{Keychain, PATTERNS_ADDRESS, schemas_from_network},
    paths::{Bip32Path, unharden},
    payment_request::PaymentRequestVerifier,
    proto::{
        common::button_request::ButtonRequestType,
        definitions::EthereumTokenInfo,
        ethereum::{EthereumSignTx, EthereumTxRequest},
    },
    rlp::{self, RLPItem},
    tokens,
};
#[cfg(not(test))]
use alloc::{string::String, vec, vec::Vec};
use primitive_types::U256;
#[cfg(test)]
use std::{string::String, vec, vec::Vec};
use trezor_app_sdk::{Error, Result, crypto, info, ui, unwrap};

// Compile-time assertion
const _: () = assert!(SC_ARGUMENT_ADDRESS_BYTES <= SC_ARGUMENT_BYTES);

// EIP-7702
const EIP_7702_TX_TYPE: u32 = 4;

// Maximum chain_id which returns the full signature_v (which must fit into an uint32).
// chain_ids larger than this will only return one bit and the caller must recalculate
// the full value: v = 2 * chain_id + 35 + v_bit
const MAX_CHAIN_ID: u64 = (0xFFFF_FFFF - 36) / 2;

// EIP-7702
const ADDR_EIP7702_UNISWAP: [u8; 20] = [
    0x00, 0x00, 0x00, 0x00, 0x9b, 0x1d, 0x0a, 0xf2, 0x0d, 0x8c, 0x6d, 0x0a, 0x44, 0xe1, 0x62, 0xd1,
    0x1f, 0x9b, 0x8f, 0x00,
];
const ADDR_EIP7702_ALCHEMY: [u8; 20] = [
    0x69, 0x00, 0x77, 0x02, 0x76, 0x41, 0x79, 0xf1, 0x4f, 0x51, 0xcd, 0xce, 0x75, 0x2f, 0x4f, 0x77,
    0x5d, 0x74, 0xe1, 0x39,
];
const ADDR_EIP7702_AMBIRE: [u8; 20] = [
    0x5a, 0x7f, 0xc1, 0x13, 0x97, 0xe9, 0xa8, 0xad, 0x41, 0xbf, 0x10, 0xbf, 0x13, 0xf2, 0x2b, 0x0a,
    0x63, 0xf9, 0x6f, 0x6d,
];
const ADDR_EIP7702_METAMASK: [u8; 20] = [
    0x63, 0xc0, 0xc1, 0x9a, 0x28, 0x2a, 0x1b, 0x52, 0xb0, 0x7d, 0xd5, 0xa6, 0x5b, 0x58, 0x94, 0x8a,
    0x07, 0xda, 0xe3, 0x2b,
];
const ADDR_EIP7702_EF_AA: [u8; 20] = [
    0x4c, 0xd2, 0x41, 0xe8, 0xd1, 0x51, 0x0e, 0x30, 0xb2, 0x07, 0x63, 0x97, 0xaf, 0xc7, 0x50, 0x8a,
    0xe5, 0x9c, 0x66, 0xc9,
];
const ADDR_EIP7702_LUGANODES: [u8; 20] = [
    0x17, 0xc1, 0x1f, 0xdd, 0xad, 0xac, 0x2b, 0x34, 0x1f, 0x24, 0x55, 0xaf, 0xe9, 0x88, 0xfe, 0xc4,
    0xc3, 0xba, 0x26, 0xe3,
];

const EIP7702_KNOWN_ADDRESSES: [([u8; 20], &str); 6] = [
    (ADDR_EIP7702_UNISWAP, "Uniswap"),
    (ADDR_EIP7702_ALCHEMY, "alchemyplatform"),
    (ADDR_EIP7702_AMBIRE, "AmbireTech"),
    (ADDR_EIP7702_METAMASK, "MetaMask"),
    (ADDR_EIP7702_EF_AA, "Ethereum Foundation AA team"),
    (ADDR_EIP7702_LUGANODES, "Luganodes"),
];

fn get_eip_7702_known_address(addr: &[u8]) -> Option<&'static str> {
    EIP7702_KNOWN_ADDRESSES
        .iter()
        .find(|(a, _)| a.as_slice() == addr)
        .map(|(_, name)| *name)
}

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

    check_common_fields(&msg)?;

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
        msg.tx_type,
        &address_bytes,
        &maximum_fee,
        &fee_items_ref,
        data_total,
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

fn check_common_fields(msg: &EthereumSignTx) -> Result<()> {
    let data_length = msg.data_length.ok_or(Error::DataError)?;
    let data_initial_chunk = msg.data_initial_chunk.as_deref().ok_or(Error::DataError)?;
    let to = msg.to.as_deref().ok_or(Error::DataError)?;

    info!("checking data length and initial chunk");
    if data_length > 0 {
        // TODO: proper error type: DataError("Data length provided, but no initial chunk")
        if data_initial_chunk.is_empty() {
            info!("Data length provided, but no initial chunk");
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

    info!("checking chain id");
    if msg.chain_id == 0 {
        // TODO: proper error type: DataError("Chain ID out of bounds")
        info!("Chain ID out of bounds");
        return Err(Error::DataError);
    }

    Ok(())
}

fn confirm_tx_data(
    msg: &EthereumSignTx,
    definitions: &Definitions,
    tx_type: Option<u32>,
    address_bytes: &[u8],
    maximum_fee: &str,
    fee_items: &[(&str, &str, bool)],
    data_total_len: u32,
    payment_req_verifier: Option<PaymentRequestVerifier>,
) -> Result<()> {
    let dp = Bip32Path::from_slice(&msg.address_n);
    let data_initial_chunk = msg.data_initial_chunk.as_deref().ok_or(Error::DataError)?;
    let value = msg.value.as_deref().ok_or(Error::DataError)?;

    if true
        == run_staking_approver(
            &dp,
            data_initial_chunk,
            value,
            &definitions.network(),
            address_bytes,
            maximum_fee,
            fee_items,
        )?
    {
        return Ok(());
    }

    info!("checking if transaction is a known contract call");
    if matches!(tx_type, Some(EIP_7702_TX_TYPE)) {
        // we have already made sure that the address is a known address
        // as part of the initial validation

        info!("authorizing smart account");

        ui::error_if_not_confirmed(ui::confirm_value(
            "Smart accounts",
            unwrap!(get_eip_7702_known_address(&address_bytes)),
            Some("Authorize the following contract as an EIP-7702 on your account?"),
            Some("confirm_provider"),
            ButtonRequestType::ButtonRequestOther.into(),
            true,
            None,
            None,
            false,
            false,
            false,
            false,
            false,
            false,
            None,
        )?)?;
    }

    info!("handling known contract calls");
    let (token, token_address, func_sig, recipient, value) =
        handle_known_contract_calls(msg, definitions, address_bytes)?;

    info!("recipient len is {}", recipient.len());

    info!(
        "func sig len is {}",
        func_sig.as_ref().map(|s| s.len()).unwrap_or(0)
    );
    let is_approve = func_sig.as_deref() == Some(SC_FUNC_SIG_APPROVE.as_slice());
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
                !is_contract_interaction && msg.tx_type != Some(EIP_7702_TX_TYPE),
                msg.chunkify.unwrap_or(false),
            )?;
        };
    };

    Ok(())
}

fn handle_known_contract_calls(
    msg: &EthereumSignTx,
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
    let data_length = msg.data_length.ok_or(Error::DataError)?;
    let value_bytes = msg.value.as_deref().ok_or(Error::DataError)?;
    let to = msg.to.as_deref().ok_or(Error::DataError)?;

    let mut token = None;
    let mut token_address = None;
    let mut recipient = Vec::from(address_bytes);

    // TODO: better implement parsing int value from bytes
    assert!(value_bytes.len() <= 32);
    let mut value = Some(U256::from_big_endian(value_bytes));

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
        && value_bytes.len() == 0
        && data_length == 68
        && data_initial_chunk.len() == 68
        && (matches!(func_sig.as_deref(), Some(sig) if sig == &SC_FUNC_SIG_TRANSFER)
            || matches!( func_sig.as_deref(), Some(sig) if sig == &SC_FUNC_SIG_APPROVE))
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

        if matches!(func_sig.as_deref(), Some(sig) if sig == &SC_FUNC_SIG_APPROVE)
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

use crate::{
    EthereumMessages, common,
    definitions::{self, Definitions},
    helpers::{
        address_from_bytes, bytes_from_address, format_ethereum_amount, get_fee_items_regular,
    },
    keychain::{Keychain, PATTERNS_ADDRESS, schemas_from_network},
    paths::Bip32Path,
    proto::{
        common::button_request::ButtonRequestType,
        definitions::{EthereumNetworkInfo, EthereumTokenInfo},
        ethereum::{EthereumSignTx, EthereumTxAck, EthereumTxRequest},
    },
    rlp::{self, RLPItem},
    strutil::{hex_decode, hex_encode},
    tokens, uformat, wire_request,
};
#[cfg(not(test))]
use alloc::{collections::BTreeMap, string::String, vec, vec::Vec};
#[cfg(test)]
use std::{collections::BTreeMap, string::String, vec, vec::Vecs};
use trezor_app_sdk::{Error, Result, crypto, info, print, ui, unwrap};

// Smart contract 'data' field lengths in bytes
const SC_FUNC_SIG_BYTES: usize = 4;
const SC_ARGUMENT_BYTES: usize = 32;
const SC_ARGUMENT_ADDRESS_BYTES: usize = 20;
const SC_FUNC_APPROVE_REVOKE_AMOUNT: u128 = 0;

// Compile-time assertion
const _: () = assert!(SC_ARGUMENT_ADDRESS_BYTES <= SC_ARGUMENT_BYTES);

// Known ERC-20 functions
fn sc_func_sig_transfer() -> Vec<u8> {
    hex_decode("a9059cbb").unwrap()
}

fn sc_func_sig_approve() -> Vec<u8> {
    hex_decode("095ea7b3").unwrap()
}

fn sc_func_sig_stake() -> Vec<u8> {
    hex_decode("3a29dbae").unwrap()
}

fn sc_func_sig_unstake() -> Vec<u8> {
    hex_decode("76ec871c").unwrap()
}

fn sc_func_sig_claim() -> Vec<u8> {
    hex_decode("33986ffa").unwrap()
}

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

// Everstake staking

// addresses for pool (stake/unstake) and accounting (claim) operations
pub fn addresses_pool() -> Vec<Vec<u8>> {
    vec![
        unwrap!(hex_decode("AFA848357154a6a624686b348303EF9a13F63264")), // Hoodi testnet
        unwrap!(hex_decode("D523794C879D9eC028960a231F866758e405bE34")), // mainnet
    ]
}

pub fn addresses_accounting() -> Vec<Vec<u8>> {
    vec![
        unwrap!(hex_decode("624087DD1904ab122A32878Ce9e933C7071F53B9")), // Hoodi testnet
        unwrap!(hex_decode("7a7f0b3c23C23a31cFcb0c44709be70d4D545c6e")), // mainnet
    ]
}

// Approve known addresses
// This should eventually grow into a more comprehensive database and stored in some other way,
// but for now let's just keep a few known addresses here!
pub fn get_approve_known_addresses() -> BTreeMap<Vec<u8>, &'static str> {
    let mut map = BTreeMap::new();
    map.insert(
        hex_decode("e592427a0aece92de3edee1f18e0157c05861564").unwrap(),
        "Uniswap V3 Router",
    );
    map.insert(
        hex_decode("111111125421cA6dc452d289314280a0f8842A65").unwrap(),
        "1inch Aggregation Router V6",
    );
    map.insert(
        hex_decode("1231DEB6f5749EF6cE6943a275A1D3E7486F4EaE").unwrap(),
        "LiFI Diamond",
    );
    map
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
    .unwrap();

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

        if !get_eip_7702_known_addresses().contains_key(&address_bytes) {
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

    // TODO: better implement parsing int value from bytes
    let mut buf = [0u8; 16];
    buf[16 - msg.gas_price.len()..].copy_from_slice(&msg.gas_price);
    let gas_price = u128::from_be_bytes(buf);

    // TODO: better implement parsing int value from bytes
    let mut buf = [0u8; 16];
    buf[16 - msg.gas_limit.len()..].copy_from_slice(&msg.gas_limit);
    let gas_limit = u128::from_be_bytes(buf);

    let maximum_fee =
        format_ethereum_amount(gas_price * gas_limit, None, &definitions.network(), false);
    let fee_items = get_fee_items_regular(gas_price, gas_limit, &definitions.network());

    let fee_items_ref: Vec<(&str, &str, bool)> = fee_items
        .iter()
        .map(|(k, v, mono)| (k.as_str(), v.as_str(), *mono))
        .collect();

    let payment_req_verifier: Option<u32> = if let Some(req) = &msg.payment_req {
        // TODO: implement
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
        rlp::write(&mut rlp_buffer, &RLPItem::Int(tx_type as u64));
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
        let resp = send_request_chunk(data_left)?;

        data_left -= resp.data_chunk.len() as u32;
        rlp_buffer.extend_from_slice(&resp.data_chunk);

        ui::update_progress(
            None,
            500 + ((initial_data_left - data_left) / initial_data_left * 400),
        )?;
    }

    // EIP-155 replay protection
    rlp::write(&mut rlp_buffer, &RLPItem::Int(msg.chain_id));
    rlp::write(&mut rlp_buffer, &RLPItem::Int(0));
    rlp::write(&mut rlp_buffer, &RLPItem::Int(0));

    let mut helper = String::new();

    for byte in &rlp_buffer {
        helper.push_str(&uformat!("{} ", *byte));
    }
    info!(
        "RLP encoded transaction: {} with len {}",
        helper.as_str(),
        rlp_buffer.len()
    );

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

fn check_common_fields(msg: &EthereumSignTx) -> Result<()> {
    let data_length = msg.data_length.ok_or(Error::DataError)?;
    let data_initial_chunk = msg.data_initial_chunk.as_deref().ok_or(Error::DataError)?;
    let to = msg.to.as_deref().ok_or(Error::DataError)?;

    if data_length > 0 {
        // TODO: proper error type: DataError("Data length provided, but no initial chunk")
        if data_initial_chunk.is_empty() {
            return Err(Error::DataError);
        }

        // Our encoding only supports transactions up to 2^24 bytes. To
        // prevent exceeding the limit we use a stricter limit on data length.
        if data_length > 16_000_000 {
            // TODO: proper error type: DataError("Data length exceeds limit")
            return Err(Error::DataError);
        }

        if data_initial_chunk.len() > data_length as usize {
            // TODO: proper error type: DataError("Invalid size of initial chunk")
            return Err(Error::DataError);
        }
    }

    if !matches!(to.len(), 0 | 40 | 42) {
        // TODO: proper error type: DataError("Invalid recipient address")
        return Err(Error::DataError);
    }

    if to.is_empty() && data_length == 0 {
        // sending transaction to address 0 (contract creation) without a data field
        // TODO: proper error type: DataError("Contract creation without data")
        return Err(Error::DataError);
    }

    if msg.chain_id == 0 {
        // TODO: proper error type: DataError("Chain ID out of bounds")
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
    // TODO: implement type for payment_req_verifier
    payment_req_verifier: Option<u32>,
) -> Result<()> {
    let dp = Bip32Path::from_slice(&msg.address_n);
    let data_initial_chunk = msg.data_initial_chunk.as_deref().ok_or(Error::DataError)?;

    run_staking_approver(
        &msg,
        &definitions.network(),
        address_bytes,
        maximum_fee,
        fee_items,
    )?;

    info!("checking if transaction is a known contract call");
    if matches!(msg.tx_type, Some(EIP_7702_TX_TYPE)) {
        // we have already made sure that the address is a known address
        // as part of the initial validation

        ui::error_if_not_confirmed(ui::confirm_value(
            "Smart accounts",
            unwrap!(get_eip_7702_known_addresses().get(address_bytes)),
            None,
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
        )?)?;
    }

    info!("handling known contract calls");
    let (token, token_address, func_sig, recipient, value) =
        handle_known_contract_calls(msg, definitions, address_bytes)?;

    let is_approve = func_sig.as_deref() == Some(sc_func_sig_approve().as_slice());
    let is_unknown_token = &token == &Some(tokens::unknown_token());

    if is_unknown_token {
        let title = String::from(if is_approve {
            if matches!(value, Some(SC_FUNC_APPROVE_REVOKE_AMOUNT)) {
                "Token revocation"
            } else {
                "Token approval"
            }
        } else {
            "Send"
        });

        if !is_approve {
            // For unknown tokens we also show the token address immediately after the warning
            // except in the case of the "approve" flow which shows the token address later on!
            common::require_confirm_address(
                address_bytes,
                Some("Send"),
                Some("Token contract address"),
                None,
                Some("Continue"),
                Some("unknown_token"),
                Some("Unknown contract address"),
            )?
        }
    }

    if is_approve {
        info!("handling approve flow");
        assert!(token.is_some());
        assert!(token_address.is_some());

        // info!("token len is {:?}", token.map(|t| t.len()));
        info!(
            "token address len is {:?}",
            token_address.as_deref().map(|a| a.len())
        );

        // DataError("Payment Requests not supported for the APPROVE call")
        assert!(payment_req_verifier.is_none());

        require_confirm_approve(
            &recipient,
            value,
            &dp,
            maximum_fee,
            fee_items,
            msg.chain_id,
            &definitions.network,
            &token.unwrap(),
            &token_address.unwrap(),
            msg.chunkify.unwrap_or(false),
        )?;
    } else {
        info!("handling regular transaction flow");
        assert!(value.is_some());

        let recipient_str = address_from_bytes(&recipient, Some(definitions.network()));
        let token_address_str = address_from_bytes(address_bytes, Some(definitions.network()));
        let is_contract_interaction = token.is_none() && data_total_len > 0;

        if let Some(payment_req_verifier) = payment_req_verifier {
            // TODO: implement payment_req_verifier
            return Err(Error::InvalidFunction);
        } else {
            if is_contract_interaction {
                require_confirm_other_data(data_initial_chunk, data_total_len)?;
            };

            require_confirm_tx(
                Some(&recipient_str),
                unwrap!(value),
                &dp,
                maximum_fee,
                fee_items,
                definitions.network(),
                token.as_ref(),
                !is_contract_interaction && !matches!(msg.tx_type, Some(EIP_7702_TX_TYPE)),
                msg.chunkify.unwrap_or(false),
            )?;
        };
    };

    Ok(())
}

fn require_confirm_tx(
    recipient: Option<&str>,
    value: u128,
    dp: &Bip32Path,
    maximum_fee: &str,
    fee_info_items: &[(&str, &str, bool)],
    network: &EthereumNetworkInfo,
    token: Option<&EthereumTokenInfo>,
    is_send: bool,
    chunkify: bool,
) -> Result<()> {
    let total_amount = format_ethereum_amount(value, token, network, false);
    let (account, account_path) = dp.account_and_path();

    confirm_ethereum_tx(
        recipient,
        &total_amount,
        account.as_deref(),
        account_path.as_deref(),
        maximum_fee,
        fee_info_items,
        is_send,
        None,
        None,
        chunkify,
    )?;
    Ok(())
}

fn confirm_ethereum_tx(
    recipient: Option<&str>,
    total_amount: &str,
    account: Option<&str>,
    account_path: Option<&str>,
    maximum_fee: &str,
    fee_info_items: &[(&str, &str, bool)],
    is_send: bool,
    br_name: Option<&str>,
    br_code: Option<i32>,
    chunkify: bool,
) -> Result<()> {
    let br_name = br_name.unwrap_or("confirm_total");
    let br_code = br_code.unwrap_or(ButtonRequestType::ButtonRequestSignTx.into());

    let subtitle = if !is_send && recipient.is_none() {
        None
    } else if is_send {
        Some("Recipient")
    } else {
        Some("Interaction contract")
    };
    let title = "Send";

    let account_properties = get_account_info_items(account, account_path);
    let menu_items = &[ui::Details::new(
        "Account info",
        &account_properties,
        None,
        Some("Send from"),
        ButtonRequestType::ButtonRequestOther.into(),
    )];

    let menu = ui::Menu::new(menu_items, Some(ui::Cancel::new("Cancel sign")));

    let steps: [&dyn Fn() -> ui::UiResult; 2] = [
        &|| {
            ui::interact_with_menu_flow(
                |name| {
                    ui::confirm_value(
                        title,
                        recipient.unwrap_or("New contract will be deployed"),
                        None,
                        name,
                        ButtonRequestType::ButtonRequestOther.into(),
                        recipient.is_some(),
                        Some("Continue"),
                        subtitle,
                        false,
                        false,
                        if recipient.is_some() { chunkify } else { false },
                        false,
                        false,
                        true,
                    )
                },
                &menu,
                Some("confirm_output"),
            )
        },
        &|| {
            ui::confirm_summary(
                Some(title),
                Some(total_amount),
                Some("Amount"),
                maximum_fee,
                "Maximum fee",
                None,
                None,
                Some("Fee info"),
                Some(fee_info_items),
                true,
                Some(br_name),
                br_code,
            )
        },
    ];

    ui::error_if_not_confirmed(ui::confirm_linear_flow(&steps)?)?;

    Ok(())
}

fn get_account_info_items<'a>(
    account: Option<&'a str>,
    account_path: Option<&'a str>,
) -> Vec<(&'a str, &'a str, bool)> {
    let mut items = Vec::with_capacity(2);
    account.map(|acc| items.push(("Account", acc, false)));
    account_path.map(|path| items.push(("Derivation path", path, false)));

    items
}

fn require_confirm_other_data(data: &[u8], data_total: u32) -> Result<()> {
    let description = uformat!("Size: {} bytes", data_total);
    let subtitle = uformat!("All input data ({} bytes)", data_total);
    let data_str = hex_encode(data);
    ui::error_if_not_confirmed(ui::confirm_blob(
        "Input data",
        &data_str,
        Some(&description),
        Some(&subtitle),
        "confirm_data",
        ButtonRequestType::ButtonRequestSignTx.into(),
        false,
        Some("Confirm"),
        Some("Cancel sign"),
        true,
        true,
    )?)?;
    Ok(())
}

fn require_confirm_approve(
    to_bytes: &[u8],
    value: Option<u128>,
    dp: &Bip32Path,
    maximum_fee: &str,
    fee_info_items: &[(&str, &str, bool)],
    chain_id: u64,
    network: &EthereumNetworkInfo,
    token: &EthereumTokenInfo,
    token_address: &[u8],
    chunkify: bool,
) -> Result<()> {
    let recipient_str = get_approve_known_addresses().get(to_bytes).copied();
    let recipient_addr = address_from_bytes(to_bytes, Some(network));
    let chain_id_str = uformat!("{} ({:x})", chain_id, chain_id);
    let token_address_str = address_from_bytes(token_address, Some(network));
    let total_amount = if let Some(value) = value {
        Some(format_ethereum_amount(value, Some(token), network, false))
    } else {
        None
    };
    let (account, account_path) = dp.account_and_path();

    let is_unknown_token = token == &tokens::unknown_token();
    let is_unknown_network = network == &definitions::unknown_network();

    info!("value is {:?}", value);
    info!("recipient address is {}", recipient_addr.as_str());
    info!("to bytes len is {}", to_bytes.len());

    confirm_ethereum_approve(
        &recipient_addr,
        recipient_str,
        is_unknown_token,
        &token_address_str,
        &token.symbol,
        is_unknown_network,
        &chain_id_str,
        &network.name,
        value == Some(SC_FUNC_APPROVE_REVOKE_AMOUNT),
        total_amount.as_deref(),
        account.as_deref(),
        account_path.as_deref(),
        maximum_fee,
        fee_info_items,
        chunkify,
    )?;
    Ok(())
}

fn confirm_ethereum_approve(
    recipient_addr: &str,
    recipient_str: Option<&str>,
    is_unknown_token: bool,
    token_address: &str,
    token_symbol: &str,
    is_unknown_network: bool,
    chain_id: &str,
    network_name: &str,
    is_revoke: bool,
    total_amount: Option<&str>,
    account: Option<&str>,
    account_path: Option<&str>,
    maximum_fee: &str,
    fee_info_items: &[(&str, &str, bool)],
    chunkify: bool,
) -> Result<()> {
    let br_name = "confirm_ethereum_approve";
    let br_code = ButtonRequestType::ButtonRequestOther.into();
    let (title, action) = if is_revoke {
        (
            "Token revocation",
            "Review details to revoke token approval.",
        )
    } else {
        (
            "Token approval",
            "Review details to approve token spending.",
        )
    };

    ui::error_if_not_confirmed(ui::confirm_action(
        title,
        action,
        false,
        Some("Continue"),
        Some(br_name),
        ButtonRequestType::ButtonRequestOther.into(),
    )?)?;

    let subtitle = if is_revoke {
        "Revoke from"
    } else {
        "Approve to"
    };

    if let Some(recipient_str) = recipient_str {
        info!("recipient str is {}", recipient_str);
        ui::interact_with_info_flow(
            |name| {
                ui::confirm_value(
                    title,
                    recipient_str,
                    None,
                    Some(br_name),
                    br_code,
                    true,
                    Some("Continue"),
                    Some(subtitle),
                    true,
                    false,
                    false,
                    false,
                    false,
                    false,
                )
            },
            |name| {
                ui::show_info_with_cancel(
                    title,
                    &[("", recipient_addr, true)],
                    chunkify,
                    name,
                    br_code,
                )
            },
            br_name,
            None,
            None,
        )?;
    } else {
        info!("recipient str is None, showing address {}", recipient_addr);
        ui::error_if_not_confirmed(ui::confirm_value(
            title,
            recipient_addr,
            None,
            Some(br_name),
            br_code,
            true,
            Some("Continue"),
            Some(subtitle),
            false,
            false,
            chunkify,
            false,
            true,
            false,
        )?)?;
    };

    if total_amount.is_none() {
        let content = uformat!("Approving unlimited amount of {}", token_symbol);
        ui::show_warning(
            title,
            &content,
            Some(br_name),
            ButtonRequestType::ButtonRequestWarning.into(),
        )?;
    }

    if is_unknown_token {
        ui::error_if_not_confirmed(ui::confirm_value(
            "Send",
            token_address,
            None,
            Some(br_name),
            ButtonRequestType::ButtonRequestOther.into(),
            true,
            None,
            None,
            false,
            false,
            chunkify,
            false,
            true,
            false,
        )?)?;
    }

    if is_unknown_network {
        ui::error_if_not_confirmed(ui::confirm_value(
            title,
            chain_id,
            Some("Chain ID"),
            Some(br_name),
            ButtonRequestType::ButtonRequestOther.into(),
            true,
            None,
            None,
            false,
            false,
            false,
            false,
            true,
            false,
        )?)?;
    }

    let mut props = Vec::with_capacity(2);
    if is_revoke {
        props.push(("Token", token_symbol, true));
    } else {
        props.push((
            "Amount allowance",
            total_amount.unwrap_or("Unlimited"),
            false,
        ));
    }
    if !is_unknown_network {
        props.push(("Chain", network_name, false));
    }

    ui::error_if_not_confirmed(ui::confirm_properties(
        title,
        &props,
        None,
        Some("Continue"),
        false,
        Some(br_name),
        ButtonRequestType::ButtonRequestOther.into(),
    )?)?;

    let account_item = account_path.map(|p| [("Derivation path", p, true)]);

    ui::error_if_not_confirmed(ui::confirm_summary(
        Some(title),
        None,
        None,
        maximum_fee,
        "Maximum fee",
        None,
        account_item.as_ref().map(|a| a.as_slice()),
        Some("Fee info"),
        Some(fee_info_items),
        false,
        Some("confirm_total"),
        ButtonRequestType::ButtonRequestOther.into(),
    )?)?;

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
    Option<u128>,
)> {
    let data_initial_chunk = msg.data_initial_chunk.as_deref().ok_or(Error::DataError)?;
    let data_length = msg.data_length.ok_or(Error::DataError)?;
    let value_bytes = msg.value.as_deref().ok_or(Error::DataError)?;
    let to = msg.to.as_deref().ok_or(Error::DataError)?;

    let mut token = None;
    let mut token_address = None;
    let mut recipient = Vec::new();

    // TODO: better implement parsing int value from bytes
    let mut buf = [0u8; 16];
    assert!(value_bytes.len() <= 16);
    buf[16 - value_bytes.len()..].copy_from_slice(value_bytes);
    let mut value = Some(u128::from_be_bytes(buf));

    let mut offset = 0;
    let mut remaining = data_initial_chunk.len();

    if remaining < SC_FUNC_SIG_BYTES {
        return Ok((token, token_address, None, Vec::from(address_bytes), value));
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
        && (matches!(func_sig.as_deref(), Some(sig) if sig == sc_func_sig_transfer())
            || matches!( func_sig.as_deref(), Some(sig) if sig == &sc_func_sig_approve()))
    {
        // The two functions happen to have the exact same parameters, so we treat them together.
        // This will need to be made into a more generic solution eventually.
        // arg0: address, Address, 20 bytes (left padded with zeroes)
        // arg1: value, uint256, 32 bytes

        if remaining < SC_ARGUMENT_BYTES * 2 {
            return Ok((token, token_address, None, Vec::from(address_bytes), value));
        }

        let arg0 = &data_initial_chunk[offset..(offset + SC_ARGUMENT_BYTES)];
        offset += SC_ARGUMENT_BYTES;
        remaining -= SC_ARGUMENT_BYTES;

        let pad_len = SC_ARGUMENT_BYTES - SC_ARGUMENT_ADDRESS_BYTES;
        assert!(arg0[..pad_len].iter().all(|&byte| byte == 0));
        recipient = Vec::from(&arg0[pad_len..]);

        let arg1: &_ = &data_initial_chunk[offset..(offset + SC_ARGUMENT_BYTES)];
        offset += SC_ARGUMENT_BYTES;
        remaining -= SC_ARGUMENT_BYTES;

        if matches!(func_sig.as_deref(), Some(sig) if sig == &sc_func_sig_approve())
            && arg1.iter().all(|&byte| byte == 255)
        {
            // "Unlimited" approval (all bits set) is a special case
            // which we encode as value=None internally.
            func_sig = None;
            info!("Detected unlimited approval, treating value as None");
        } else {
            // TODO: better implement parsing int value from bytes
            let mut buf = [0u8; 16];
            assert!(value_bytes.len() <= 16);
            buf.copy_from_slice(&arg1[16..]);
            value = Some(u128::from_be_bytes(buf));
            info!("Parsed value from function arguments: {:?}", value);
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

/// Runs confirmation for ETH staking approval for staking related transactions.
fn run_staking_approver<'a>(
    msg: &'a EthereumSignTx,
    network: &'a EthereumNetworkInfo,
    address_bytes: &'a [u8],
    maximum_fee: &'a str,
    fee_items: &'a [(&'a str, &'a str, bool)],
) -> Result<()> {
    let data_initial_chunk = msg.data_initial_chunk.as_deref().ok_or(Error::DataError)?;

    if data_initial_chunk.len() < SC_FUNC_SIG_BYTES {
        return Ok(());
    }

    let func_sig = &data_initial_chunk[..SC_FUNC_SIG_BYTES];
    let data = &data_initial_chunk[SC_FUNC_SIG_BYTES..];
    if addresses_pool()
        .iter()
        .any(|addr| addr.as_slice() == address_bytes)
    {
        if func_sig == sc_func_sig_stake().as_slice() {
            handle_staking_tx_stake(data, msg, network, address_bytes, maximum_fee, fee_items)?;
        } else if func_sig == sc_func_sig_unstake().as_slice() {
            handle_staking_tx_unstake(data, msg, network, address_bytes, maximum_fee, fee_items)?;
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
                msg.chunkify.unwrap_or(false),
            )?;
        }
    }

    Ok(())
}

fn handle_staking_tx_claim(
    data: &[u8],
    msg: &EthereumSignTx,
    staking_address: &[u8],
    maximum_fee: &str,
    fee_items: &[(&str, &str, bool)],
    network: &EthereumNetworkInfo,
    chunkify: bool,
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
        chunkify,
    )?;

    Ok(())
}

fn require_confirm_claim(
    address_bytes: &[u8],
    dp: &Bip32Path,
    maximum_fee: &str,
    fee_info_items: &[(&str, &str, bool)],
    network: &EthereumNetworkInfo,
    chunkify: bool,
) -> Result<()> {
    let addr_str = address_from_bytes(address_bytes, Some(network));
    let (account, account_path) = dp.account_and_path();

    confirm_ethereum_staking_tx(
        "Claim",
        "Claim ETH from Everstake?",
        "Claim",
        "",
        account.as_deref(),
        account_path.as_deref(),
        maximum_fee,
        &addr_str,
        "Claim address",
        fee_info_items,
        chunkify,
        None,
        None,
    )?;

    Ok(())
}

fn handle_staking_tx_unstake(
    data: &[u8],
    msg: &EthereumSignTx,
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
    let mut buf = [0u8; 16];
    buf.copy_from_slice(&arg0[SC_ARGUMENT_BYTES - 16..]);
    let value = u128::from_be_bytes(buf);

    // skip arg1 and arg2

    require_confirm_unstake(
        address_bytes,
        value,
        &Bip32Path::from_slice(&msg.address_n),
        maximum_fee,
        fee_items,
        network,
        msg.chunkify.unwrap_or(false),
    )?;

    Ok(())
}

fn require_confirm_unstake(
    address_bytes: &[u8],
    value: u128,
    dp: &Bip32Path,
    maximum_fee: &str,
    fee_info_items: &[(&str, &str, bool)],
    network: &EthereumNetworkInfo,
    chunkify: bool,
) -> Result<()> {
    let address_str = address_from_bytes(address_bytes, Some(network));
    let total_amount = format_ethereum_amount(value, None, network, false);
    let (account, account_path) = dp.account_and_path();

    confirm_ethereum_staking_tx(
        "Unstake",
        "Unstake ETH on Everstake?",
        "Unstake",
        &total_amount,
        account.as_deref(),
        account_path.as_deref(),
        maximum_fee,
        &address_str,
        "Stake address",
        fee_info_items,
        chunkify,
        None,
        None,
    )?;

    Ok(())
}

fn handle_staking_tx_stake(
    data: &[u8],
    msg: &EthereumSignTx,
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

    let value_bytes = msg.value.as_deref().ok_or(Error::DataError)?;
    let mut buf = [0u8; 16];
    assert!(value_bytes.len() <= 16);
    buf[16 - value_bytes.len()..].copy_from_slice(value_bytes);
    let value = u128::from_be_bytes(buf);

    require_confirm_stake(
        address_bytes,
        value,
        &Bip32Path::from_slice(&msg.address_n),
        maximum_fee,
        fee_items,
        network,
        msg.chunkify.unwrap_or(false),
    )?;

    Ok(())
}

fn require_confirm_stake(
    address_bytes: &[u8],
    value: u128,
    dp: &Bip32Path,
    maximum_fee: &str,
    fee_info_items: &[(&str, &str, bool)],
    network: &EthereumNetworkInfo,
    chunkify: bool,
) -> Result<()> {
    let address_str = address_from_bytes(address_bytes, Some(network));
    let total_amount = format_ethereum_amount(value, None, network, false);
    let (account, account_path) = dp.account_and_path();

    confirm_ethereum_staking_tx(
        "Stake",
        "Stake ETH on Everstake?",
        "Stake",
        &total_amount,
        account.as_deref(),
        account_path.as_deref(),
        maximum_fee,
        &address_str,
        "Stake address",
        fee_info_items,
        chunkify,
        None,
        None,
    )?;

    Ok(())
}

fn confirm_ethereum_staking_tx(
    title: &str,
    intro_question: &str,
    verb: &str,
    total_amount: &str,
    account: Option<&str>,
    account_path: Option<&str>,
    maximum_fee: &str,
    address: &str,
    address_title: &str,
    info_items: &[(&str, &str, bool)],
    chunkify: bool,
    br_name: Option<&str>,
    br_code: Option<i32>,
) -> Result<()> {
    assert!(verb == "Stake" || verb == "Unstake" || verb == "Claim");

    let br_name = br_name.unwrap_or("confirm_ethereum_staking_tx");
    let br_code = br_code.unwrap_or(ButtonRequestType::ButtonRequestSignTx.into());

    let mut menu_items = Vec::with_capacity(2);
    let props = [(address, "", false)];
    menu_items.push(ui::Details::new(
        address_title,
        &props,
        None,
        None,
        ButtonRequestType::ButtonRequestOther.into(),
    ));

    let account_properties = get_account_info_items(account, account_path);
    if !account_properties.is_empty() {
        menu_items.push(ui::Details::new(
            "Account info",
            &account_properties,
            None,
            Some("Send from"),
            ButtonRequestType::ButtonRequestOther.into(),
        ));
    };

    let amount_label = if verb == "Claim" {
        None
    } else {
        Some("Amount")
    };

    let menu = ui::Menu::new(menu_items.as_slice(), Some(ui::Cancel::new("Cancel sign")));

    let steps: [&dyn Fn() -> ui::UiResult; 2] = [
        &|| {
            ui::interact_with_menu_flow(
                |name| {
                    ui::confirm_value(
                        verb,
                        intro_question,
                        None,
                        name,
                        ButtonRequestType::ButtonRequestSignTx.into(),
                        false,
                        None,
                        None,
                        false,
                        false,
                        false,
                        false,
                        false,
                        true,
                    )
                },
                &menu,
                Some(br_name),
            )
        },
        &|| {
            ui::confirm_summary(
                Some(title),
                Some(total_amount),
                amount_label,
                maximum_fee,
                "Maximum fee",
                None,
                None,
                Some("Fee info"),
                Some(info_items),
                true,
                Some("confirm_total"),
                br_code,
            )
        },
    ];
    ui::error_if_not_confirmed(ui::confirm_linear_flow(&steps)?)?;

    Ok(())
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

    let signature =
        crypto::sign_typed_hash(&msg.address_n, digest, encoded_network, encoded_token)?;

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

fn send_request_chunk(data_left: u32) -> Result<EthereumTxAck> {
    let req_size = core::cmp::min(data_left, 1024);
    info!(
        "requesting data chunk with {} bytes left with {} bytes",
        data_left, req_size
    );

    let mut req = EthereumTxRequest::default();
    req.data_length = Some(core::cmp::min(data_left, 1024) as u32);

    let resp: EthereumTxAck = wire_request(&req, EthereumMessages::TxRequest)?;

    Ok(resp)
}

pub fn get_total_length(msg: &EthereumSignTx, data_total: u32) -> Result<u32> {
    let mut length = 0;

    if let Some(tx_type) = msg.tx_type {
        length += rlp::length(&RLPItem::Int(tx_type as u64));
        info!(
            "tx_type length: {}",
            rlp::length(&RLPItem::Int(tx_type as u64))
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
        RLPItem::Int(msg.chain_id),
        RLPItem::Int(0),
        RLPItem::Int(0),
    ];

    for field in &fields {
        length += rlp::length(field);
        info!("field length: {}", rlp::length(field));
    }

    length += rlp::header_length(data_total, Some(data_initial_chunk));
    length += data_total;

    Ok(length)
}

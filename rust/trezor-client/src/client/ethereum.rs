use super::{handle_interaction, Trezor};
use crate::{
    error::Result,
    protos::{
        self,
        ethereum_sign_tx_eip1559::EthereumAccessList,
        ethereum_typed_data_struct_ack::{
            EthereumDataType, EthereumFieldType, EthereumStructMember,
        },
        EthereumTxRequest,
    },
    Error,
};

/// Access list item.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AccessListItem {
    /// Accessed address
    pub address: String,
    /// Accessed storage keys
    pub storage_keys: Vec<Vec<u8>>,
}

/// An ECDSA signature.
#[derive(Debug, Clone, PartialEq, Eq, Copy)]
pub struct Signature {
    /// R value
    pub r: [u8; 32],
    /// S Value
    pub s: [u8; 32],
    /// V value in 'Electrum' notation.
    pub v: u64,
}

impl Trezor {
    // ETHEREUM
    pub fn ethereum_get_address(&mut self, path: Vec<u32>) -> Result<String> {
        let mut req = protos::EthereumGetAddress::new();
        req.address_n = path;
        let address = handle_interaction(
            self.call(req, Box::new(|_, m: protos::EthereumAddress| Ok(m.address().into())))?,
        )?;
        Ok(address)
    }

    pub fn ethereum_sign_message(&mut self, message: Vec<u8>, path: Vec<u32>) -> Result<Signature> {
        let mut req = protos::EthereumSignMessage::new();
        req.address_n = path;
        req.set_message(message);
        let signature = handle_interaction(self.call(
            req,
            Box::new(|_, m: protos::EthereumMessageSignature| {
                let signature = m.signature();
                if signature.len() != 65 {
                    return Err(Error::MalformedSignature);
                }
                let r = signature[0..32].try_into().unwrap();
                let s = signature[32..64].try_into().unwrap();
                let v = signature[64] as u64;
                Ok(Signature { r, s, v })
            }),
        )?)?;

        Ok(signature)
    }

    #[allow(clippy::too_many_arguments)]
    pub fn ethereum_sign_tx(
        &mut self,
        path: Vec<u32>,
        nonce: Vec<u8>,
        gas_price: Vec<u8>,
        gas_limit: Vec<u8>,
        to: String,
        value: Vec<u8>,
        data: Vec<u8>,
        chain_id: Option<u64>,
    ) -> Result<Signature> {
        let mut req = protos::EthereumSignTx::new();
        let mut data = data;

        req.address_n = path;
        req.set_nonce(nonce);
        req.set_gas_price(gas_price);
        req.set_gas_limit(gas_limit);
        req.set_value(value);
        if let Some(chain_id) = chain_id {
            req.set_chain_id(chain_id);
        }
        req.set_to(to);

        req.set_data_length(data.len() as u32);
        req.set_data_initial_chunk(data.splice(..std::cmp::min(1024, data.len()), []).collect());

        let mut resp =
            handle_interaction(self.call(req, Box::new(|_, m: protos::EthereumTxRequest| Ok(m)))?)?;

        while resp.data_length() > 0 {
            let mut ack = protos::EthereumTxAck::new();
            ack.set_data_chunk(data.splice(..std::cmp::min(1024, data.len()), []).collect());

            resp = handle_interaction(
                self.call(ack, Box::new(|_, m: protos::EthereumTxRequest| Ok(m)))?,
            )?;
        }

        convert_signature(&resp, chain_id)
    }

    #[allow(clippy::too_many_arguments)]
    pub fn ethereum_sign_eip1559_tx(
        &mut self,
        path: Vec<u32>,
        nonce: Vec<u8>,
        gas_limit: Vec<u8>,
        to: String,
        value: Vec<u8>,
        data: Vec<u8>,
        chain_id: Option<u64>,
        max_gas_fee: Vec<u8>,
        max_priority_fee: Vec<u8>,
        access_list: Vec<AccessListItem>,
    ) -> Result<Signature> {
        let mut req = protos::EthereumSignTxEIP1559::new();
        let mut data = data;

        req.address_n = path;
        req.set_nonce(nonce);
        req.set_max_gas_fee(max_gas_fee);
        req.set_max_priority_fee(max_priority_fee);
        req.set_gas_limit(gas_limit);
        req.set_value(value);
        if let Some(chain_id) = chain_id {
            req.set_chain_id(chain_id);
        }
        req.set_to(to);

        if !access_list.is_empty() {
            req.access_list = access_list
                .into_iter()
                .map(|item| EthereumAccessList {
                    address: Some(item.address),
                    storage_keys: item.storage_keys,
                    ..Default::default()
                })
                .collect();
        }

        req.set_data_length(data.len() as u32);
        req.set_data_initial_chunk(data.splice(..std::cmp::min(1024, data.len()), []).collect());

        let mut resp =
            handle_interaction(self.call(req, Box::new(|_, m: protos::EthereumTxRequest| Ok(m)))?)?;

        while resp.data_length() > 0 {
            let mut ack = protos::EthereumTxAck::new();
            ack.set_data_chunk(data.splice(..std::cmp::min(1024, data.len()), []).collect());

            resp = handle_interaction(
                self.call(ack, Box::new(|_, m: protos::EthereumTxRequest| Ok(m)))?,
            )?;
        }

        convert_signature(&resp, chain_id)
    }

    pub fn ethereum_sign_typed_hash(
        &mut self,
        path: Vec<u32>,
        domain_separator_hash: Vec<u8>,
        message_hash: Option<Vec<u8>>,
    ) -> Result<Signature> {
        let mut req = protos::EthereumSignTypedHash::new();
        req.address_n = path;
        req.set_domain_separator_hash(domain_separator_hash);
        if let Some(hash) = message_hash {
            req.set_message_hash(hash);
        }
        let sig = handle_interaction(self.call(
            req,
            Box::new(|_, m: protos::EthereumTypedDataSignature| {
                let signature = m.signature();
                if signature.len() != 65 {
                    return Err(Error::MalformedSignature);
                }
                let r = signature[0..32].try_into().unwrap();
                let s = signature[32..64].try_into().unwrap();
                let v = signature[64] as u64;
                Ok(Signature { r, s, v })
            }),
        )?)?;
        Ok(sig)
    }

    /// Signs EIP-712 typed data using the streaming protocol.
    ///
    /// Takes JSON representations of the EIP-712 types, domain, and message.
    /// `types` is a map of struct name to array of {name, type} objects.
    /// `domain` and `message` are the JSON values to sign.
    pub fn ethereum_sign_typed_data(
        &mut self,
        path: Vec<u32>,
        primary_type: &str,
        types: &serde_json::Map<String, serde_json::Value>,
        domain: &serde_json::Value,
        message: &serde_json::Value,
    ) -> Result<Signature> {
        use serde_json::Value;

        let mut req = protos::EthereumSignTypedData::new();
        req.address_n = path;
        req.set_primary_type(primary_type.to_string());
        req.set_metamask_v4_compat(true);

        let mut resp = self.call_raw(req)?;

        loop {
            match resp.message_type() {
                protos::MessageType::MessageType_EthereumTypedDataSignature => {
                    let sig: protos::EthereumTypedDataSignature = resp.into_message()?;
                    let signature = sig.signature();
                    if signature.len() != 65 {
                        return Err(Error::MalformedSignature);
                    }
                    return Ok(Signature {
                        r: signature[0..32].try_into().unwrap(),
                        s: signature[32..64].try_into().unwrap(),
                        v: signature[64] as u64,
                    });
                }
                protos::MessageType::MessageType_Failure => {
                    let f: protos::Failure = resp.into_message()?;
                    return Err(Error::FailureResponse(f));
                }
                protos::MessageType::MessageType_ButtonRequest => {
                    let _: protos::ButtonRequest = resp.into_message()?;
                    resp = self.call_raw(protos::ButtonAck::new())?;
                }
                // PIN and passphrase handling mirrors handle_interaction():
                // PIN entry is not supported (no interactive callback available
                // in the streaming loop), passphrase defaults to on-device or
                // empty string for standard (no-passphrase) wallets.
                protos::MessageType::MessageType_PinMatrixRequest => {
                    return Err(Error::UnsupportedNetwork);
                }
                protos::MessageType::MessageType_PassphraseRequest => {
                    let pr: protos::PassphraseRequest = resp.into_message()?;
                    let mut ack = protos::PassphraseAck::new();
                    if pr._on_device() {
                        ack.set_on_device(true);
                    } else {
                        ack.set_passphrase(String::new());
                    }
                    resp = self.call_raw(ack)?;
                }
                protos::MessageType::MessageType_EthereumTypedDataStructRequest => {
                    let sr: protos::EthereumTypedDataStructRequest = resp.into_message()?;
                    let struct_name = sr.name().to_string();

                    let mut ack = protos::EthereumTypedDataStructAck::new();
                    if let Some(Value::Array(fields)) = types.get(&struct_name) {
                        for field in fields {
                            let name = field.get("name").and_then(|v| v.as_str()).unwrap_or("");
                            let ty = field.get("type").and_then(|v| v.as_str()).unwrap_or("");
                            let mut member = EthereumStructMember::new();
                            member.set_name(name.to_string());
                            member.type_ = protobuf::MessageField::some(
                                make_field_type(ty, types),
                            );
                            ack.members.push(member);
                        }
                    }
                    resp = self.call_raw(ack)?;
                }
                protos::MessageType::MessageType_EthereumTypedDataValueRequest => {
                    let vr: protos::EthereumTypedDataValueRequest = resp.into_message()?;
                    let member_path = vr.member_path.clone();

                    let root_index = member_path[0];
                    let (mut type_name, mut value) = if root_index == 0 {
                        ("EIP712Domain".to_string(), domain.clone())
                    } else {
                        (primary_type.to_string(), message.clone())
                    };

                    for &index in &member_path[1..] {
                        match &value {
                            Value::Object(map) => {
                                if let Some(Value::Array(fields)) = types.get(&type_name) {
                                    if let Some(field) = fields.get(index as usize) {
                                        let fname = field.get("name").and_then(|v| v.as_str()).unwrap_or("");
                                        let ftype = field.get("type").and_then(|v| v.as_str()).unwrap_or("");
                                        type_name = ftype.to_string();
                                        value = map.get(fname).cloned().unwrap_or(Value::Null);
                                    }
                                }
                            }
                            Value::Array(arr) => {
                                type_name = strip_array_suffix(&type_name);
                                value = arr.get(index as usize).cloned().unwrap_or(Value::Null);
                            }
                            _ => {}
                        }
                    }

                    let encoded = if let Value::Array(arr) = &value {
                        (arr.len() as u16).to_be_bytes().to_vec()
                    } else {
                        encode_typed_value(&value, &type_name)
                    };

                    let mut ack = protos::EthereumTypedDataValueAck::new();
                    ack.set_value(encoded);
                    resp = self.call_raw(ack)?;
                }
                other => {
                    return Err(Error::UnexpectedMessageType(other));
                }
            }
        }
    }
}

fn make_field_type(
    type_name: &str,
    types: &serde_json::Map<String, serde_json::Value>,
) -> EthereumFieldType {
    let mut ft = EthereumFieldType::new();

    if type_name.ends_with(']') {
        ft.set_data_type(EthereumDataType::ARRAY);
        let inner = strip_array_suffix(type_name);
        if let Some(bracket) = type_name.rfind('[') {
            let size_str = &type_name[bracket + 1..type_name.len() - 1];
            if let Ok(n) = size_str.parse::<u32>() {
                ft.set_size(n);
            }
        }
        ft.entry_type = protobuf::MessageField::some(make_field_type(&inner, types));
    } else if let Some(rest) = type_name.strip_prefix("uint") {
        ft.set_data_type(EthereumDataType::UINT);
        if let Ok(bits) = rest.parse::<u32>() {
            ft.set_size(bits / 8);
        }
    } else if let Some(rest) = type_name.strip_prefix("int") {
        ft.set_data_type(EthereumDataType::INT);
        if let Ok(bits) = rest.parse::<u32>() {
            ft.set_size(bits / 8);
        }
    } else if type_name == "bytes" {
        ft.set_data_type(EthereumDataType::BYTES);
    } else if let Some(rest) = type_name.strip_prefix("bytes") {
        ft.set_data_type(EthereumDataType::BYTES);
        if let Ok(n) = rest.parse::<u32>() {
            ft.set_size(n);
        }
    } else if type_name == "string" {
        ft.set_data_type(EthereumDataType::STRING);
    } else if type_name == "bool" {
        ft.set_data_type(EthereumDataType::BOOL);
    } else if type_name == "address" {
        ft.set_data_type(EthereumDataType::ADDRESS);
    } else if types.contains_key(type_name) {
        ft.set_data_type(EthereumDataType::STRUCT);
        if let Some(serde_json::Value::Array(fields)) = types.get(type_name) {
            ft.set_size(fields.len() as u32);
        }
        ft.set_struct_name(type_name.to_string());
    }

    ft
}

fn strip_array_suffix(type_name: &str) -> String {
    match type_name.rfind('[') {
        Some(idx) => type_name[..idx].to_string(),
        None => type_name.to_string(),
    }
}

fn encode_uint_be(s: &str, byte_len: usize) -> Vec<u8> {
    let byte_len = byte_len.min(32);
    let mut buf = [0u8; 32];
    let hex_str = s.strip_prefix("0x").or_else(|| s.strip_prefix("0X"));
    if let Some(hex_str) = hex_str {
        if let Ok(decoded) = hex::decode(hex_str) {
            let len = decoded.len().min(32);
            let start = 32 - len;
            buf[start..start + len].copy_from_slice(&decoded[..len]);
        }
    } else if let Ok(n) = s.parse::<u128>() {
        buf[16..].copy_from_slice(&n.to_be_bytes());
    }
    buf[32 - byte_len..].to_vec()
}

fn encode_int_be(s: &str, byte_len: usize) -> Vec<u8> {
    let byte_len = byte_len.min(32);
    let n = s.parse::<i128>().unwrap_or(0);
    let mut buf = if n < 0 { [0xffu8; 32] } else { [0u8; 32] };
    buf[16..].copy_from_slice(&n.to_be_bytes());
    buf[32 - byte_len..].to_vec()
}

fn encode_typed_value(value: &serde_json::Value, type_name: &str) -> Vec<u8> {
    use serde_json::Value;

    match value {
        Value::String(s) => {
            if type_name == "string" {
                s.as_bytes().to_vec()
            } else if type_name == "address" {
                hex::decode(s.strip_prefix("0x").unwrap_or(s)).unwrap_or_default()
            } else if type_name.starts_with("bytes") {
                hex::decode(s.strip_prefix("0x").unwrap_or(s)).unwrap_or_default()
            } else if type_name.starts_with("uint") {
                encode_uint_be(s, parse_type_size(type_name) / 8)
            } else if type_name.starts_with("int") {
                encode_int_be(s, parse_type_size(type_name) / 8)
            } else {
                s.as_bytes().to_vec()
            }
        }
        Value::Number(n) => {
            let byte_len = parse_type_size(type_name) / 8;
            if type_name.starts_with("uint") {
                let val = n.as_u64().unwrap_or(0);
                encode_uint_be(&val.to_string(), byte_len)
            } else if type_name.starts_with("int") {
                let val = n.as_i64().unwrap_or(0);
                encode_int_be(&val.to_string(), byte_len)
            } else {
                vec![]
            }
        }
        Value::Bool(b) => vec![*b as u8],
        _ => vec![],
    }
}

fn parse_type_size(type_name: &str) -> usize {
    type_name
        .chars()
        .rev()
        .take_while(|c| c.is_ascii_digit())
        .collect::<String>()
        .chars()
        .rev()
        .collect::<String>()
        .parse::<usize>()
        .unwrap_or(256)
}

fn convert_signature(resp: &EthereumTxRequest, chain_id: Option<u64>) -> Result<Signature> {
    let mut v = resp.signature_v() as u64;
    if let Some(chain_id) = chain_id {
        if v <= 1 {
            v = v + 2 * chain_id + 35;
        }
    }
    let r = resp.signature_r().try_into().map_err(|_| Error::MalformedSignature)?;
    let s = resp.signature_s().try_into().map_err(|_| Error::MalformedSignature)?;
    Ok(Signature { r, s, v })
}

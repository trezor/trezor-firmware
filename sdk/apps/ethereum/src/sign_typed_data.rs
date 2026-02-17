extern crate alloc;

use crate::common::require_confirm_address;
use crate::definitions::{Definitions, unknown_network};
use crate::helpers::address_from_bytes;
use crate::helpers::decode_typed_data;
use crate::keychain::Keychain;
use crate::keychain::PATTERNS_ADDRESS;
use crate::paths::{Bip32Path, PathSchema};
use crate::proto::definitions::EthereumNetworkInfo;
use crate::proto::ethereum::EthereumTypedDataSignature;
use crate::proto::ethereum_eip712::{
    EthereumSignTypedData, EthereumTypedDataStructAck, EthereumTypedDataStructRequest,
    EthereumTypedDataValueAck, EthereumTypedDataValueRequest,
    ethereum_typed_data_struct_ack::{EthereumDataType, EthereumFieldType, EthereumStructMember},
};
use crate::strutil::hex_encode;
use crate::{uformat, wire_request};
use alloc::string::ToString;
use alloc::vec::Vec;
use alloc::{
    collections::{BTreeMap, BTreeSet},
    string::String,
    vec,
};
use trezor_app_sdk::{
    crypto::{self, keccak_256},
    ui, unwrap, {Error, Result},
};

/// Ethereum uses Bitcoin xpub format
pub fn sign_typed_data(msg: EthereumSignTypedData) -> Result<EthereumTypedDataSignature> {
    let dp = Bip32Path::from_slice(&msg.address_n);

    let slip44 = dp.slip44();
    let definitions = Definitions::from_encoded(None, None, None, slip44).unwrap();

    let schemas = schemas_from_network(&PATTERNS_ADDRESS, definitions.slip44())?;
    let keychain = Keychain::new(schemas);

    dp.validate(&keychain)?;

    let address_bytes = crypto::get_eth_pubkey_hash(dp.as_ref())?;

    // Display address so user can validate it
    require_confirm_address(&address_bytes, None, None, None, None, None)?;

    let metamask_v4_compat = msg.metamask_v4_compat.unwrap_or(true);
    let show_message_hash = if let Some(hash) = &msg.show_message_hash {
        Some(hash.as_slice())
    } else {
        None
    };

    let data_hash = unwrap!(generate_typed_data_hash(
        &msg.primary_type,
        metamask_v4_compat,
        show_message_hash
    ));

    let signature = crypto::sign_typed_hash(dp.as_ref(), &data_hash)?;

    let mut sig = EthereumTypedDataSignature::default();
    sig.address = address_from_bytes(&address_bytes, Some(definitions.chain_id()));
    sig.signature.extend_from_slice(&signature[1..]);
    sig.signature.push(signature[0]);

    // TODO implement actual signing logic
    Ok(sig)
}

/// Generate typed data hash according to EIP-712 specification
/// https://eips.ethereum.org/EIPS/eip-712#specification
///
/// # Arguments
/// * `primary_type` - The primary type from the EIP-712 message
/// * `metamask_v4_compat` - A flag that enables compatibility with MetaMask's signTypedData_v4 method
/// * `show_message_hash` - Optional message hash to display

fn generate_typed_data_hash(
    primary_type: &str,
    metamask_v4_compat: bool,
    show_message_hash: Option<&[u8]>,
) -> Result<[u8; 32]> {
    let mut data_envelope = TypedDataEnvelope::new(primary_type, metamask_v4_compat);

    data_envelope.collect_types()?;

    let (name, version) = get_name_and_version_for_domain(&data_envelope)?;

    let show_domain = should_show_domain(&name, &version)?;

    let domain_separator =
        data_envelope.hash_struct("EIP712Domain", &[0], show_domain, &["EIP712Domain"])?;

    // Setting the primary_type to "EIP712Domain" is technically in spec
    // In this case, we ignore the "message" part and only use the "domain" part
    // https://ethereum-magicians.org/t/eip-712-standards-clarification-primarytype-as-domaintype/3286
    let message_hash = if primary_type == "EIP712Domain" {
        confirm_empty_typed_message()?;
        [0u8; 32]
    } else {
        let show_message = should_show_struct(
            primary_type,
            unwrap!(data_envelope.types.get(primary_type))
                .members
                .as_slice(),
            Some("<title>"),
            Some("<button_text>"),
        )?;
        data_envelope.hash_struct(primary_type, &[1], show_message, &[primary_type])?
    };

    if let Some(show_message_hash) = show_message_hash {
        if show_message_hash != &message_hash {
            // TODO Message hash mismatch
            return Err(Error::InvalidMessage);
        }

        confirm_message_hash(&message_hash)?;
    }

    confirm_typed_data_final()?;

    let mut data = Vec::new();
    data.extend_from_slice(b"\x19\x01");
    data.extend_from_slice(&domain_separator);
    data.extend_from_slice(&message_hash);
    Ok(keccak_256(&data))
}

/// Encapsulates the type information for the message being hashed and signed.
pub struct TypedDataEnvelope {
    primary_type: String,
    metamask_v4_compat: bool,
    types: BTreeMap<String, EthereumTypedDataStructAck>,
}

impl TypedDataEnvelope {
    pub fn new(primary_type: &str, metamask_v4_compat: bool) -> Self {
        Self {
            primary_type: primary_type.to_string(),
            metamask_v4_compat,
            types: BTreeMap::new(),
        }
    }

    pub fn collect_types(&mut self) -> Result<()> {
        let primary_type = self.primary_type.clone();
        self._collect_types("EIP712Domain")?;
        self._collect_types(&primary_type)?;
        Ok(())
    }

    /// Recursively collect types from the client.
    fn _collect_types(&mut self, type_name: &str) -> Result<()> {
        let req = EthereumTypedDataStructRequest {
            name: type_name.to_string(),
        };

        let current_type: EthereumTypedDataStructAck = unwrap!(wire_request(&req));
        let members = current_type.members.clone();
        self.types.insert(type_name.to_string(), current_type);

        for member in members.iter() {
            let mut member_type = &member.r#type;
            validate_field_type(&member_type)?;
            while member_type.data_type == EthereumDataType::Array as i32 {
                if let Some(entry_type) = &member_type.entry_type {
                    member_type = entry_type;
                } else {
                    return Err(Error::InvalidMessage);
                }
            }
            if member_type.data_type == EthereumDataType::Struct as i32 {
                if let Some(struct_name) = &member_type.struct_name {
                    if !self.types.contains_key(struct_name) {
                        self._collect_types(struct_name)?;
                    }
                } else {
                    return Err(Error::InvalidMessage);
                }
            }
        }
        Ok(())
    }

    /// Generate a hash representation of the whole struct.
    fn hash_struct(
        &self,
        primary_type: &str,
        member_value_path: &[u32],
        show_data: bool,
        parent_objects: &[&str],
    ) -> Result<[u8; 32]> {
        // TODO: implement actual hashing logic
        Ok([0u8; 32])
    }

    /// The type of a struct is encoded as name ‖ "(" ‖ member₁ ‖ "," ‖ member₂ ‖ "," ‖ … ‖ memberₙ ")"
    /// where each member is written as type ‖ " " ‖ name
    /// If the struct type references other struct types (and these in turn reference even more struct types),
    /// then the set of referenced struct types is collected, sorted by name and appended to the encoding.
    fn encode_type(&self, primary_type: &str) -> Result<Vec<String>> {
        return Ok(vec![]); // TODO: implement actual encoding logic
    }

    fn find_typed_dependencies(
        &self,
        primary_type: &str,
        results: &mut BTreeSet<String>,
    ) -> Result<()> {
        // We already have this type or it is not even a defined type
        if results.contains(primary_type) || !self.types.contains_key(primary_type) {
            return Ok(());
        }

        results.insert(primary_type.to_string());

        // Recursively add all child struct types, also looking into arrays
        let members = &self
            .types
            .get(primary_type)
            .ok_or(Error::InvalidMessage)?
            .members;

        for member in members {
            let mut member_type = &member.r#type;

            while member_type.data_type == EthereumDataType::Array as i32 {
                member_type = member_type
                    .entry_type
                    .as_ref()
                    .ok_or(Error::InvalidMessage)?;
            }

            if member_type.data_type == EthereumDataType::Struct as i32 {
                let struct_name = member_type
                    .struct_name
                    .as_ref()
                    .ok_or(Error::InvalidMessage)?;
                self.find_typed_dependencies(struct_name, results)?;
            }
        }

        Ok(())
    }
}

fn validate_field_type(field: &EthereumFieldType) -> Result<()> {
    let data_type = field.data_type;

    // entry_type is only for arrays
    if data_type == EthereumDataType::Array as i32 {
        let entry = field.entry_type.as_ref().ok_or(Error::InvalidMessage)?;
        validate_field_type(entry)?;
    } else if field.entry_type.is_some() {
        return Err(Error::InvalidMessage);
    }

    // struct_name is only for structs
    if data_type == EthereumDataType::Struct as i32 {
        if field.struct_name.is_none() {
            return Err(Error::InvalidMessage);
        }
    } else if field.struct_name.is_some() {
        return Err(Error::InvalidMessage);
    }

    let size = field.size;

    // size is special for each type
    if data_type == EthereumDataType::Struct as i32 {
        if size.is_none() {
            return Err(Error::InvalidMessage);
        }
    } else if data_type == EthereumDataType::Bytes as i32 {
        if let Some(s) = size {
            if !(1..=32).contains(&s) {
                return Err(Error::InvalidMessage);
            }
        }
    } else if data_type == EthereumDataType::Uint as i32
        || data_type == EthereumDataType::Int as i32
    {
        if let Some(s) = size {
            if !(1..=32).contains(&s) {
                return Err(Error::InvalidMessage);
            }
        } else {
            return Err(Error::InvalidMessage);
        }
    } else if data_type == EthereumDataType::String as i32
        || data_type == EthereumDataType::Bool as i32
        || data_type == EthereumDataType::Address as i32
    {
        if size.is_some() {
            return Err(Error::InvalidMessage);
        }
    }

    Ok(())
}

fn get_name_and_version_for_domain(
    typed_data_envelope: &TypedDataEnvelope,
) -> Result<(Vec<u8>, Vec<u8>)> {
    let mut domain_name = b"unknown".to_vec();
    let mut domain_version = b"unknown".to_vec();

    let domain_members = typed_data_envelope
        .types
        .get("EIP712Domain")
        .ok_or(Error::InvalidMessage)?
        .members
        .iter();

    let mut member_value_path = [0u32, 0u32];
    for (member_index, member) in domain_members.enumerate() {
        member_value_path[1] = member_index as u32;
        if member.name == "name" {
            domain_name = get_value(&member.r#type, &member_value_path)?;
        } else if member.name == "version" {
            domain_version = get_value(&member.r#type, &member_value_path)?;
        }
    }

    Ok((domain_name, domain_version))
}

/// Get a single value from the client and perform its validation.
fn get_value(field: &EthereumFieldType, member_value_path: &[u32]) -> Result<Vec<u8>> {
    let req = EthereumTypedDataValueRequest {
        member_path: member_value_path.iter().map(|&v| v).collect(),
    };

    let res: EthereumTypedDataValueAck = unwrap!(wire_request(&req));
    let value = res.value;

    validate_value(field, &value)?;
    Ok(value)
}

/// Make sure the byte data we receive are not corrupted or incorrect.
///
/// Return an error if encountering a problem, so clients are notified.
fn validate_value(field: &EthereumFieldType, value: &[u8]) -> Result<()> {
    // Size check
    if let Some(size) = field.size {
        if value.len() != size as usize {
            return Err(Error::InvalidMessage);
        }
    }

    // Type-specific checks
    match field.data_type {
        x if x == EthereumDataType::Bool as i32 => {
            if value != [0x00] && value != [0x01] {
                // TODO Invalid boolean value
                return Err(Error::InvalidMessage);
            }
        }
        x if x == EthereumDataType::Address as i32 => {
            if value.len() != 20 {
                // TODO Invalid address length
                return Err(Error::InvalidMessage);
            }
        }
        x if x == EthereumDataType::String as i32 => {
            if core::str::from_utf8(value).is_err() {
                // TODO Invalid UTF-8 string
                return Err(Error::InvalidMessage);
            }
        }
        _ => {}
    }

    Ok(())
}

fn should_show_domain(name: &[u8], version: &[u8]) -> Result<bool> {
    let domain_name = decode_typed_data(name, "string")?;
    let domain_version = decode_typed_data(version, "string")?;

    // TODO: implement actual logic to decide whether to show the domain or not. For now, we just show it if it's not "unknown".
    Ok(true)
}

fn confirm_empty_typed_message() -> Result<()> {
    // TODO: implement actual confirmation logic
    Ok(())
}

fn should_show_struct(
    description: &str,
    data_members: &[EthereumStructMember],
    title: Option<&str>,
    button_text: Option<&str>,
) -> Result<bool> {
    // TODO
    Ok(true)
}

fn confirm_message_hash(hash: &[u8]) -> Result<()> {
    let message_hash_hex = uformat!("0x{}", hex_encode(hash).as_str());
    ui::confirm_value("CConfirm message hash", &message_hash_hex)?;
    Ok(())
}

fn confirm_typed_data_final() -> Result<()> {
    match ui::confirm_action("confirm typed ", "Really sign EIP-712 typed data?", true)? {
        ui::TrezorUiResult::Confirmed => Ok(()),
        _ => Err(Error::Cancelled),
    }
}

pub fn schemas_from_network(patterns: &[&str], slip44: u32) -> Result<Vec<PathSchema>> {
    let slip44_id: Vec<u32> = if slip44 == unknown_network().slip44 {
        // allow Ethereum or testnet paths for unknown networks
        vec![60, 1]
    } else if slip44 != 60 {
        // allow cross-signing with Ethereum for all non-mainnet networks
        vec![slip44, 60]
    } else {
        // legacy testnet slip44 = 1
        vec![slip44, 1]
    };

    let schemas = patterns
        .iter()
        .map(|p| PathSchema::parse(p, &slip44_id))
        .collect::<Result<Vec<_>>>()?;

    Ok(schemas)
}

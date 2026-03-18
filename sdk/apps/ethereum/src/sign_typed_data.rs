use crate::{EthereumMessages, helpers::get_type_name, uformat, wire_request};
use crate::{
    common::require_confirm_address,
    definitions::Definitions,
    helpers::{address_from_bytes, decode_typed_data},
    keychain::{Keychain, PATTERNS_ADDRESS, schemas_from_network},
    paths::Bip32Path,
    proto::{
        common::button_request::ButtonRequestType,
        ethereum::EthereumTypedDataSignature,
        ethereum_eip712::{
            EthereumSignTypedData, EthereumTypedDataStructAck, EthereumTypedDataStructRequest,
            EthereumTypedDataValueAck, EthereumTypedDataValueRequest,
            ethereum_typed_data_struct_ack::{
                EthereumDataType, EthereumFieldType, EthereumStructMember,
            },
        },
    },
    strutil::hex_encode,
};
#[cfg(not(test))]
use alloc::{
    collections::{BTreeMap, BTreeSet},
    string::String,
    string::ToString,
    vec,
    vec::Vec,
};
#[cfg(test)]
use std::{
    collections::{BTreeMap, BTreeSet},
    string::String,
    string::ToString,
    vec,
    vec::Vec,
};
use trezor_app_sdk::{
    Error, Result,
    crypto::{self, keccak_256},
    info, ui, unwrap,
};

/// Ethereum uses Bitcoin xpub format
pub fn sign_typed_data(msg: EthereumSignTypedData) -> Result<EthereumTypedDataSignature> {
    info!("Signing typed data");
    let dp = Bip32Path::from_slice(&msg.address_n);

    let slip44 = dp.slip44();
    let definitions = Definitions::from_encoded(
        msg.definitions
            .as_ref()
            .and_then(|d| d.encoded_network.as_ref().map(|v| v.as_slice())),
        msg.definitions
            .as_ref()
            .and_then(|d| d.encoded_token.as_ref().map(|v| v.as_slice())),
        None,
        slip44,
    )
    .unwrap();

    let schemas = schemas_from_network(&PATTERNS_ADDRESS, definitions.slip44())?;
    let keychain = Keychain::new(schemas);

    dp.validate(&keychain)?;

    let (encoded_network, encoded_token) = match &msg.definitions {
        Some(def) => (
            def.encoded_network.as_ref().map(|d| d.as_ref()),
            def.encoded_token.as_ref().map(|d| d.as_ref()),
        ),
        None => (None, None),
    };

    info!("Getting pubkey hash");
    let address_bytes = crypto::get_eth_pubkey_hash(dp.as_ref(), encoded_network, encoded_token)?;

    // Display address so user can validate it
    info!("require Confirm address");
    require_confirm_address(&address_bytes, None, None, None, None, None, None)?;

    info!("Address confirmed, proceeding with signing");
    let metamask_v4_compat = msg.metamask_v4_compat.unwrap_or(true);
    let show_message_hash = if let Some(hash) = &msg.show_message_hash {
        Some(hash.as_slice())
    } else {
        None
    };
    info!("Generating typed data hash");

    let data_hash = unwrap!(generate_typed_data_hash(
        &msg.primary_type,
        metamask_v4_compat,
        show_message_hash
    ));

    let signature =
        crypto::sign_typed_hash(dp.as_ref(), &data_hash, encoded_network, encoded_token)?;

    let mut sig = EthereumTypedDataSignature::default();
    sig.address = address_from_bytes(&address_bytes, Some(definitions.network()));
    sig.signature.extend_from_slice(&signature[1..]);
    sig.signature.push(signature[0]);

    info!("Typed data signed successfully");
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
    info!("Collecting type information from client");
    let mut data_envelope = TypedDataEnvelope::new(primary_type, metamask_v4_compat);

    info!("Collecting types");
    data_envelope.collect_types()?;

    info!("getting name and version");
    let (name, version) = get_name_and_version_for_domain(&data_envelope)?;

    info!("Determining whether to show domain information");
    let show_domain = should_show_domain(&name, &version)?;

    let domain_separator =
        data_envelope.hash_struct("EIP712Domain", &[0], show_domain, &["EIP712Domain"])?;

    // Setting the primary_type to "EIP712Domain" is technically in spec
    // In this case, we ignore the "message" part and only use the "domain" part
    // https://ethereum-magicians.org/t/eip-712-standards-clarification-primarytype-as-domaintype/3286
    let message_hash = if primary_type == "EIP712Domain" {
        info!("empty typed message");
        confirm_empty_typed_message()?;
        [0u8; 32]
    } else {
        info!("Determining whether to show struct");
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
            // TODO: proper error type: Message hash mismatch
            return Err(Error::InvalidMessage);
        }

        info!("Confirming message hash with user");
        confirm_message_hash(&message_hash)?;
    }

    info!("Confirming final signing action with user");
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
        info!("primary type {}", primary_type.as_str());
        self._collect_types("EIP712Domain")?;
        self._collect_types(&primary_type)?;
        Ok(())
    }

    /// Recursively collect types from the client.
    fn _collect_types(&mut self, type_name: &str) -> Result<()> {
        let req = EthereumTypedDataStructRequest {
            name: type_name.to_string(),
        };

        info!("Requesting type information for {}", type_name);
        let current_type: EthereumTypedDataStructAck =
            unwrap!(wire_request(&req, EthereumMessages::TypedDataStructRequest));
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
        let data = Vec::new();
        // TODO: implement

        let hashed_type = self.hash_type(primary_type)?;

        info!("Hashing struct {}", primary_type);

        Ok(crypto::keccak_256(&data))
    }

    // TODO: implement
    fn get_and_encode_data() -> Result<()> {
        Ok(())
    }

    fn hash_type(&self, primary_type: &str) -> Result<[u8; 32]> {
        Ok(crypto::keccak_256(&self.encode_type(primary_type)?))
    }

    /// The type of a struct is encoded as name ‖ "(" ‖ member₁ ‖ "," ‖ member₂ ‖ "," ‖ … ‖ memberₙ ")"
    /// where each member is written as type ‖ " " ‖ name
    /// If the struct type references other struct types (and these in turn reference even more struct types),
    /// then the set of referenced struct types is collected, sorted by name and appended to the encoding.
    fn encode_type(&self, primary_type: &str) -> Result<Vec<u8>> {
        info!("Encoding type {}", primary_type);

        let mut result = Vec::new();

        let mut deps = BTreeSet::new();
        self.find_typed_dependencies(primary_type, &mut deps)?;
        deps.remove(primary_type);

        // Start with primary_type, then add sorted deps
        let mut types_to_process = vec![primary_type];
        types_to_process.extend(deps.iter().map(|s| s.as_str()));

        for type_name in types_to_process {
            let type_def = self.types.get(type_name).ok_or(Error::DataError)?;
            let members = &type_def.members;

            let fields = members
                .iter()
                .map(|m| {
                    let type_name = get_type_name(&m.r#type)?;
                    Ok(uformat!("{} {}", type_name.as_str(), m.name.as_str()))
                })
                .collect::<Result<Vec<_>>>()?
                .join(",");

            result.push(uformat!("{}({})", type_name, fields.as_str()));
        }

        let data = result.join("").into_bytes();
        Ok(data)
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

    let res: EthereumTypedDataValueAck =
        unwrap!(wire_request(&req, EthereumMessages::TypedDataValueRequest));
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
                // TODO: proper error type: Invalid boolean value
                return Err(Error::InvalidMessage);
            }
        }
        x if x == EthereumDataType::Address as i32 => {
            if value.len() != 20 {
                // TODO: proper error type: Invalid address length
                return Err(Error::InvalidMessage);
            }
        }
        x if x == EthereumDataType::String as i32 => {
            if core::str::from_utf8(value).is_err() {
                // TODO: proper error type: Invalid UTF-8 string
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

    let para = [
        ("Name and version", false),
        (&domain_name, false),
        (&domain_version, false),
    ];

    ui::should_show_more(
        "Confirm domain",
        &para,
        "Show full domain",
        Some("should_show_domain"),
    )
    .map_err(|_| Error::Cancelled)
}

fn confirm_empty_typed_message() -> Result<()> {
    confirm_text(
        "confirm_empty_typed_message",
        "Confirm message",
        "",
        Some("No message field"),
        None,
    )
}

fn confirm_text(
    br_name: &str,
    title: &str,
    data: &str,
    description: Option<&str>,
    br_code: Option<i32>,
) -> Result<()> {
    ui::confirm_value(
        title,
        data,
        description,
        Some(br_name),
        br_code.unwrap_or(ButtonRequestType::ButtonRequestOther.into()),
        false,
        Some("Confirm"),
        None,
        false,
        false,
        false,
        false,
        false,
        false,
    )?;
    Ok(())
}

fn should_show_struct(
    description: &str,
    data_members: &[EthereumStructMember],
    title: Option<&str>,
    button_text: Option<&str>,
) -> Result<bool> {
    let title = title.unwrap_or("Confirm struct");
    let button_text = button_text.unwrap_or("Show full struct");

    let contains = uformat!("Contains {} keys", data_members.len());

    let field_names = data_members
        .iter()
        .map(|field| field.name.as_str())
        .collect::<Vec<_>>()
        .join(", ");

    let para = [
        (description, false),
        (&contains, false),
        (&field_names, false),
    ];

    ui::should_show_more(title, &para, button_text, Some("should_show_struct"))
        .map_err(|_| Error::Cancelled)
}

fn confirm_message_hash(hash: &[u8]) -> Result<()> {
    let message_hash_hex = uformat!("0x{}", hex_encode(hash).as_str());
    ui::confirm_value(
        "Confirm message hash",
        &message_hash_hex,
        None,
        Some("confirm_message_hash"),
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
    )?;
    Ok(())
}

fn confirm_typed_data_final() -> Result<()> {
    match ui::confirm_action(
        "Confirm typed data",
        "Really sign EIP-712 typed data?",
        true,
        None,
        None,
        ButtonRequestType::ButtonRequestOther.into(),
    )? {
        ui::TrezorUiResult::Confirmed => Ok(()),
        _ => Err(Error::Cancelled),
    }
}

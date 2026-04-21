use crate::{
    common::require_confirm_address,
    definitions::Definitions,
    helpers::{address_from_bytes, decode_typed_data},
    keychain::{Keychain, PATTERNS_ADDRESS, schemas_from_network},
    paths::Bip32Path,
    proto::{
        common::button_request::ButtonRequestType,
        ethereum::{
            SignTypedData, TypedDataSignature, TypedDataStructAck, TypedDataStructRequest,
            TypedDataValueAck, TypedDataValueRequest,
            typed_data_struct_ack::{DataType, FieldType, StructMember},
        },
        messages::MessageType,
    },
    strutil::{format_plural_english, hex_encode},
};
use crate::{helpers::get_type_name, uformat, wire_request};
#[cfg(not(test))]
use alloc::{
    collections::{BTreeMap, BTreeSet},
    string::String,
    string::ToString,
    vec,
    vec::Vec,
};
use primitive_types::U256;
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
    info,
    ui::{self, StrExt},
    unwrap,
};

/// Ethereum uses Bitcoin xpub format
pub fn sign_typed_data(msg: SignTypedData) -> Result<TypedDataSignature> {
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
    )?;

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

    let address_bytes = crypto::get_eth_pubkey_hash(dp.as_ref(), encoded_network, encoded_token)?;

    // Display address so user can validate it
    require_confirm_address(&address_bytes, None, None, None, None, None, None)?;

    let metamask_v4_compat = msg.metamask_v4_compat.unwrap_or(true);
    let show_message_hash = if let Some(hash) = &msg.show_message_hash {
        Some(hash.as_slice())
    } else {
        None
    };

    let data_hash =
        generate_typed_data_hash(&msg.primary_type, metamask_v4_compat, show_message_hash)?;

    let signature = crypto::sign_typed_hash(
        dp.as_ref(),
        &data_hash,
        encoded_network,
        encoded_token,
        None,
    )?;

    let mut sig = TypedDataSignature::default();
    sig.address = address_from_bytes(&address_bytes, Some(definitions.network()));
    sig.signature.extend_from_slice(&signature[1..]);
    sig.signature.push(signature[0]);

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
    ui::init_progress(None, None, true, false)?;

    let mut data_envelope = TypedDataEnvelope::new(primary_type, metamask_v4_compat);

    data_envelope.collect_types(|p| p * 700f32 as u32)?;

    let (name, version) = get_name_and_version_for_domain(&data_envelope)?;

    let show_domain = should_show_domain(&name, &version)?;

    let domain_separator = data_envelope.hash_struct(
        "EIP712Domain",
        &[0],
        show_domain,
        &["EIP712Domain"],
        Some(|p| 700 + 3 * p),
    )?;

    ui::end_progress()?;

    // Setting the primary_type to "EIP712Domain" is technically in spec
    // In this case, we ignore the "message" part and only use the "domain" part
    // https://ethereum-magicians.org/t/eip-712-standards-clarification-primarytype-as-domaintype/3286
    let message_hash = if primary_type == "EIP712Domain" {
        confirm_empty_typed_message()?;
        Vec::new()
    } else {
        let show_message = should_show_struct(
            primary_type,
            unwrap!(data_envelope.types.get(primary_type))
                .members
                .as_slice(),
            Some("Confirm message"),
            Some("Show full message"),
        )?;
        ui::init_progress(None, Some("Loading transaction..."), false, false)?;
        let message_hash = data_envelope.hash_struct(
            primary_type,
            &[1],
            show_message,
            &[primary_type],
            Some(|p| 10 * p),
        )?;

        ui::end_progress()?;
        message_hash.to_vec()
    };

    if let Some(show_message_hash) = show_message_hash {
        if show_message_hash != &message_hash {
            return Err(Error::DataError("Message hash mismatch"));
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
    types: BTreeMap<String, TypedDataStructAck>,
}

impl TypedDataEnvelope {
    pub fn new(primary_type: &str, metamask_v4_compat: bool) -> Self {
        Self {
            primary_type: primary_type.to_string(),
            metamask_v4_compat,
            types: BTreeMap::new(),
        }
    }

    pub fn collect_types<F>(&mut self, map_progress: F) -> Result<()>
    where
        F: Fn(u32) -> u32 + Copy,
    {
        let primary_type = self.primary_type.clone();
        self._collect_types("EIP712Domain", Some(|p| map_progress(p) / 2))?;
        self._collect_types(&primary_type, Some(|p| map_progress(p) / 2 + 500))?;
        Ok(())
    }

    /// Recursively collect types from the client.
    fn _collect_types<F>(&mut self, type_name: &str, map_progress: Option<F>) -> Result<()>
    where
        F: Fn(u32) -> u32 + Copy,
    {
        let req = TypedDataStructRequest {
            name: type_name.to_string(),
        };

        let current_type: TypedDataStructAck =
            unwrap!(wire_request(&req, MessageType::TypedDataStructRequest));
        let members = current_type.members.clone();
        self.types.insert(type_name.to_string(), current_type);

        for (index, member) in members.iter().enumerate() {
            if let Some(map_progress) = &map_progress {
                ui::update_progress(
                    None,
                    map_progress(index as u32 * 100 / members.len() as u32),
                )?;
            }
            let mut member_type = &member.r#type;
            validate_field_type(&member_type)?;
            while member_type.data_type == DataType::Array as i32 {
                if let Some(entry_type) = &member_type.entry_type {
                    member_type = entry_type;
                } else {
                    return Err(Error::DataError("Missing member type"));
                }
            }
            if member_type.data_type == DataType::Struct as i32 {
                if let Some(struct_name) = &member_type.struct_name {
                    if !self.types.contains_key(struct_name) {
                        self._collect_types::<F>(struct_name, None)?;
                    }
                } else {
                    return Err(Error::DataError("Missing struct name"));
                }
            }
        }
        Ok(())
    }

    /// Generate a hash representation of the whole struct.
    fn hash_struct<F>(
        &self,
        primary_type: &str,
        member_value_path: &[u32],
        show_data: bool,
        parent_objects: &[&str],
        map_progress: Option<F>,
    ) -> Result<[u8; 32]>
    where
        F: Fn(u32) -> u32 + Copy,
    {
        let mut w = Vec::new();

        self.hash_type(&mut w, primary_type)?;

        self.get_and_encode_data(
            &mut w,
            primary_type,
            member_value_path,
            show_data,
            parent_objects,
            map_progress,
        )?;

        Ok(crypto::keccak_256(&w))
    }

    /// Gradually fetch data from client and encode the whole struct.
    ///
    /// SPEC:
    /// The encoding of a struct instance is enc(value₁) ‖ enc(value₂) ‖ … ‖ enc(valueₙ),
    /// i.e. the concatenation of the encoded member values in the order that they appear in the type.
    /// Each encoded member value is exactly 32-byte long.
    fn get_and_encode_data<F>(
        &self,
        w: &mut Vec<u8>,
        primary_type: &str,
        member_path: &[u32],
        show_data: bool,
        parent_objects: &[&str],
        map_progress: Option<F>,
    ) -> Result<()>
    where
        F: Fn(u32) -> u32 + Copy,
    {
        let type_members = &self
            .types
            .get(primary_type)
            .ok_or(Error::DataError("Type not found"))?
            .members;
        // let members_count = type_members.len();
        let mut member_value_path = member_path.to_vec();
        member_value_path.push(0);
        let mut current_parent_objects = parent_objects.to_vec();
        current_parent_objects.push("");

        for (member_index, member) in type_members.iter().enumerate() {
            // TODO: implement progress

            if let Some(map_progress) = &map_progress {
                ui::update_progress(
                    None,
                    map_progress(member_index as u32 * 100 / type_members.len() as u32),
                )?;
            }

            // we can unwrap because the vector is never empty
            *unwrap!(member_value_path.last_mut()) = member_index as u32;
            let field_name = &member.name;
            let field_type = &member.r#type;

            // Arrays and structs need special recursive handling
            if field_type.data_type == DataType::Struct as i32 {
                if let Some(struct_name) = &field_type.struct_name {
                    // we can unwrap because the vector is never empty
                    *unwrap!(current_parent_objects.last_mut()) = field_name;

                    let show_struct = if show_data {
                        should_show_struct(
                            struct_name,
                            &self.types[struct_name].members,
                            Some(&current_parent_objects.join(".")),
                            None,
                        )?
                    } else {
                        false
                    };

                    let hash = self.hash_struct::<F>(
                        struct_name,
                        &member_value_path,
                        show_struct,
                        &current_parent_objects,
                        None,
                    )?;
                    w.extend_from_slice(&hash);
                } else {
                    return Err(Error::DataError("Missing struct name for struct field"));
                }
            } else if field_type.data_type == DataType::Array as i32 {
                // Getting the length of the array first, if not fixed
                let array_size = field_type
                    .size
                    .unwrap_or(_get_array_size(&member_value_path)?);

                if let Some(entry_type) = &field_type.entry_type {
                    // we can unwrap because the vector is never empty
                    *unwrap!(current_parent_objects.last_mut()) = field_name;
                    let show_array = if show_data {
                        should_show_array(
                            &current_parent_objects,
                            &get_type_name(entry_type)?,
                            array_size,
                        )?
                    } else {
                        false
                    };
                    let mut arr_w = Vec::new();
                    let mut el_member_path = member_value_path.to_vec();
                    el_member_path.push(0);
                    for idx in 0..array_size {
                        // we can unwrap because the vector is never empty
                        *unwrap!(el_member_path.last_mut()) = idx as u32;
                        // TODO: we do not support arrays of arrays, check if we should
                        if entry_type.data_type == DataType::Struct as i32 {
                            if let Some(struct_name) = &entry_type.struct_name {
                                // Metamask V4 implementation has a bug, that causes the
                                // behavior of structs in array be different from SPEC
                                // Explanation at https://github.com/MetaMask/eth-sig-util/pull/107
                                // encode_data() is the way to process structs in arrays, but
                                // Metamask V4 is using hash_struct() even in this case
                                if self.metamask_v4_compat {
                                    let hash_struct = self.hash_struct::<F>(
                                        struct_name,
                                        &el_member_path,
                                        show_array,
                                        &current_parent_objects,
                                        None,
                                    )?;
                                    arr_w.extend_from_slice(&hash_struct);
                                } else {
                                    self.get_and_encode_data::<F>(
                                        &mut arr_w,
                                        struct_name,
                                        &el_member_path,
                                        show_array,
                                        &current_parent_objects,
                                        None,
                                    )?;
                                }
                            } else {
                                return Err(Error::DataError("Missing entry type for array field"));
                            }
                        } else {
                            let value = get_value(entry_type, &el_member_path)?;
                            encode_field(&mut arr_w, entry_type, &value)?;
                            if show_array {
                                confirm_typed_value(
                                    field_name,
                                    &value,
                                    &parent_objects,
                                    entry_type,
                                    Some(idx),
                                )?
                            }
                        }
                    }
                    let hash = crypto::keccak_256(&arr_w);
                    w.extend_from_slice(&hash);
                } else {
                    return Err(Error::DataError("Missing entry type for array field"));
                }
            } else {
                let value = get_value(field_type, &member_value_path)?;
                encode_field(w, field_type, &value)?;
                if show_data {
                    confirm_typed_value(field_name, &value, &parent_objects, field_type, None)?
                }
            }
        }
        Ok(())
    }

    fn hash_type(&self, w: &mut Vec<u8>, primary_type: &str) -> Result<()> {
        w.extend_from_slice(&crypto::keccak_256(&self.encode_type(primary_type)?));
        Ok(())
    }

    /// SPEC:
    /// The type of a struct is encoded as name ‖ "(" ‖ member₁ ‖ "," ‖ member₂ ‖ "," ‖ … ‖ memberₙ ")"
    /// where each member is written as type ‖ " " ‖ name
    /// If the struct type references other struct types (and these in turn reference even more struct types),
    /// then the set of referenced struct types is collected, sorted by name and appended to the encoding.
    fn encode_type(&self, primary_type: &str) -> Result<Vec<u8>> {
        let mut result = Vec::new();

        let mut deps = BTreeSet::new();
        self.find_typed_dependencies(primary_type, &mut deps)?;
        deps.remove(primary_type);

        // Start with primary_type, then add sorted deps
        let mut types_to_process = vec![primary_type];
        types_to_process.extend(deps.iter().map(|s| s.as_str()));

        for type_name in types_to_process {
            let type_def = self
                .types
                .get(type_name)
                .ok_or(Error::DataError("Type not found"))?;
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
            .ok_or(Error::DataError("Missing primary type"))?
            .members;

        for member in members {
            let mut member_type = &member.r#type;

            while member_type.data_type == DataType::Array as i32 {
                member_type = member_type
                    .entry_type
                    .as_ref()
                    .ok_or(Error::DataError("Missing entry type"))?;
            }

            if member_type.data_type == DataType::Struct as i32 {
                let struct_name = member_type
                    .struct_name
                    .as_ref()
                    .ok_or(Error::DataError("Missing struct name"))?;
                self.find_typed_dependencies(struct_name, results)?;
            }
        }

        Ok(())
    }
}

fn validate_field_type(field: &FieldType) -> Result<()> {
    let data_type = field.data_type;

    // entry_type is only for arrays
    if data_type == DataType::Array as i32 {
        let entry = field
            .entry_type
            .as_ref()
            .ok_or(Error::DataError("Missing entry type"))?;
        validate_field_type(entry)?;
    } else if field.entry_type.is_some() {
        return Err(Error::DataError("Unexpected entry type"));
    }

    // struct_name is only for structs
    if data_type == DataType::Struct as i32 {
        if field.struct_name.is_none() {
            return Err(Error::DataError("Missing struct name"));
        }
    } else if field.struct_name.is_some() {
        return Err(Error::DataError("Unexpected struct name"));
    }

    let size = field.size;

    // size is special for each type
    if data_type == DataType::Struct as i32 {
        if size.is_none() {
            return Err(Error::DataError("Missing struct size"));
        }
    } else if data_type == DataType::Bytes as i32 {
        if let Some(s) = size {
            if !(1..=32).contains(&s) {
                return Err(Error::DataError("Invalid bytes size"));
            }
        }
    } else if data_type == DataType::Uint as i32 || data_type == DataType::Int as i32 {
        if let Some(s) = size {
            if !(1..=32).contains(&s) {
                return Err(Error::DataError("Invalid integer size"));
            }
        } else {
            return Err(Error::DataError("Missing integer size"));
        }
    } else if data_type == DataType::String as i32
        || data_type == DataType::Bool as i32
        || data_type == DataType::Address as i32
    {
        if size.is_some() {
            return Err(Error::DataError("Unexpected size"));
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
        .ok_or(Error::DataError("Missing EIP712Domain type"))?
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
fn get_value(field: &FieldType, member_value_path: &[u32]) -> Result<Vec<u8>> {
    let req = TypedDataValueRequest {
        member_path: member_value_path.iter().map(|&v| v).collect(),
    };

    let res: TypedDataValueAck = unwrap!(wire_request(&req, MessageType::TypedDataValueRequest));
    let value = res.value;

    validate_value(field, &value)?;
    Ok(value)
}

/// Make sure the byte data we receive are not corrupted or incorrect.
///
/// Return an error if encountering a problem, so clients are notified.
fn validate_value(field: &FieldType, value: &[u8]) -> Result<()> {
    // Size check
    if let Some(size) = field.size {
        if value.len() != size as usize {
            return Err(Error::DataError("Invalid value size"));
        }
    }

    // Type-specific checks
    match field.data_type {
        x if x == DataType::Bool as i32 => {
            if value != [0x00] && value != [0x01] {
                return Err(Error::DataError("Invalid boolean value"));
            }
        }
        x if x == DataType::Address as i32 => {
            if value.len() != 20 {
                return Err(Error::DataError("Invalid address length"));
            }
        }
        x if x == DataType::String as i32 => {
            if core::str::from_utf8(value).is_err() {
                return Err(Error::DataError("Invalid UTF-8 string"));
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
        StrExt::new("Name and version", false),
        StrExt::new(&domain_name, false),
        StrExt::new(&domain_version, false),
    ];

    let result = ui::should_show_more(
        "Confirm domain",
        &para,
        "Show full domain",
        Some("should_show_domain"),
        ButtonRequestType::ButtonRequestOther.into(),
    )
    .map_err(|_| Error::Cancelled)?;
    Ok(result)
}

fn should_show_array(parent_objects: &[&str], data_type: &str, size: u32) -> Result<bool> {
    // Leaving english plural form because of dynamic noun - data_type
    let array_of_plural = uformat!(
        "Array of {}",
        format_plural_english(size, data_type).as_str()
    );
    let para = [StrExt::new(&array_of_plural, false)];
    ui::should_show_more(
        &limit_str(&parent_objects.to_vec().join("."), None),
        &para,
        "Show full array",
        Some("should_show_array"),
        ButtonRequestType::ButtonRequestOther.into(),
    )
    .map_err(|_| Error::Cancelled)
}

fn confirm_empty_typed_message() -> Result<()> {
    confirm_text(
        "confirm_empty_typed_message",
        "Confirm message",
        "",
        Some("No message field"),
        ButtonRequestType::ButtonRequestOther.into(),
    )
}

fn confirm_text(
    br_name: &str,
    title: &str,
    data: &str,
    description: Option<&str>,
    br_code: i32,
) -> Result<()> {
    ui::error_if_not_confirmed(ui::confirm_value(
        title,
        data,
        description,
        Some(br_name),
        br_code,
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
    Ok(())
}

fn should_show_struct(
    description: &str,
    data_members: &[StructMember],
    title: Option<&str>,
    button_text: Option<&str>,
) -> Result<bool> {
    let title = title.unwrap_or("Confirm struct");
    let button_text = button_text.unwrap_or("Show full struct");

    // TODO: implement plural form
    let contains = uformat!("Contains {} keys", data_members.len());

    let field_names = data_members
        .iter()
        .map(|field| field.name.as_str())
        .collect::<Vec<_>>()
        .join(", ");

    let para = [
        StrExt::new(description, false),
        StrExt::new(&contains, false),
        StrExt::new(&field_names, false),
    ];

    ui::should_show_more(
        title,
        &para,
        button_text,
        Some("should_show_struct"),
        ButtonRequestType::ButtonRequestOther.into(),
    )
    .map_err(|_| Error::Cancelled)
}

fn confirm_message_hash(hash: &[u8]) -> Result<()> {
    let message_hash_hex = uformat!("0x{}", hex_encode(hash).as_str());
    ui::error_if_not_confirmed(ui::confirm_value(
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
        None,
    )?)?;
    Ok(())
}

fn confirm_typed_data_final() -> Result<()> {
    match ui::confirm_action(
        "Confirm typed data",
        "Really sign EIP-712 typed data?",
        true,
        None,
        Some("confirm_typed_data_final"),
        ButtonRequestType::ButtonRequestOther.into(),
    )? {
        ui::TrezorUiResult::Confirmed => Ok(()),
        _ => Err(Error::Cancelled),
    }
}

fn confirm_typed_value(
    name: &str,
    value: &[u8],
    parent_objects: &[&str],
    field: &FieldType,
    array_idx: Option<u32>,
) -> Result<()> {
    let type_name = get_type_name(field)?;
    let mut parts: Vec<&str> = parent_objects.to_vec();

    let (title, description) = if let Some(idx) = array_idx {
        parts.push(name);
        (
            limit_str(&parts.join("."), None),
            uformat!("[{}] ({})", idx, type_name.as_str()),
        )
    } else {
        (
            limit_str(&parts.join("."), None),
            uformat!("{} ({})", name, type_name.as_str()),
        )
    };

    let data = decode_typed_data(value, &type_name)?;
    let br_name = "confirm_typed_value";
    let br_code = ButtonRequestType::ButtonRequestOther.into();

    if field.data_type == DataType::Address as i32 || field.data_type == DataType::Bytes as i32 {
        ui::error_if_not_confirmed(ui::confirm_blob(
            &title,
            &data,
            Some(&description),
            None,
            br_name,
            br_code,
            false,
            None,
            None,
            false,
            false,
            true,
        )?)?;
    } else {
        confirm_text(br_name, &title, &data, Some(&description), br_code)?;
    }

    Ok(())
}

/// Shortens string to show the last <limit> characters.
fn limit_str(s: &str, limit: Option<usize>) -> String {
    let limit = limit.unwrap_or(16);
    if s.len() <= limit + 2 {
        return s.to_string();
    }

    uformat!("..{}", &s[s.len() - limit..])
}

fn leftpad32(value: &[u8], signed: bool) -> Result<[u8; 32]> {
    if value.len() > 32 {
        return Err(Error::DataError("Value too long to encode as 32 bytes"));
    }

    // Values need to be sign-extended, so accounting for negative ints
    let pad_value = if signed && value[0] & 0x80 != 0 {
        0xFF
    } else {
        0x00
    };
    let mut res = [pad_value; 32];

    res[32 - value.len()..].copy_from_slice(value);
    Ok(res)
}

fn rightpad32(value: &[u8]) -> Result<[u8; 32]> {
    if value.len() > 32 {
        return Err(Error::DataError("Value too long to encode as 32 bytes"));
    }

    let mut res = [0; 32];

    res[..value.len()].copy_from_slice(value);
    Ok(res)
}

/// SPEC:
/// Atomic types:
/// - Boolean false and true are encoded as uint256 values 0 and 1 respectively
/// - Addresses are encoded as uint160
/// - Integer values are sign-extended to 256-bit and encoded in big endian order
/// - Bytes1 to bytes31 are arrays with a beginning (index 0)
///   and an end (index length - 1), they are zero-padded at the end to bytes32 and encoded
///   in beginning to end order
/// Dynamic types:
/// - Bytes and string are encoded as a keccak256 hash of their contents
/// Reference types:
/// - Array values are encoded as the keccak256 hash of the concatenated
///   encodeData of their contents
/// - Struct values are encoded recursively as hashStruct(value)
fn encode_field(w: &mut Vec<u8>, field: &FieldType, value: &[u8]) -> Result<()> {
    if field.data_type == DataType::Bytes as i32 {
        if let Some(_size) = field.size {
            // write_rightpad32
            w.extend_from_slice(&rightpad32(value)?);
        } else {
            w.extend_from_slice(&crypto::keccak_256(value));
        };
    } else if field.data_type == DataType::String as i32 {
        w.extend_from_slice(&crypto::keccak_256(value));
    } else if field.data_type == DataType::Int as i32 {
        w.extend_from_slice(&leftpad32(value, true)?);
    } else if field.data_type == DataType::Uint as i32
        || field.data_type == DataType::Bool as i32
        || field.data_type == DataType::Address as i32
    {
        w.extend_from_slice(&leftpad32(value, false)?);
    } else {
        return Err(Error::ValueError(
            "Unsupported data type for field encoding",
        ));
    }

    Ok(())
}

/// Get the length of an array at specific `member_path` from the client.
fn _get_array_size(member_path: &[u32]) -> Result<u32> {
    // Field type for getting the array length from client, so we can check the return value
    let array_length_type = FieldType {
        data_type: DataType::Uint as i32,
        size: Some(2),
        entry_type: None,
        struct_name: None,
    };
    let length_value = get_value(&array_length_type, member_path)?;

    Ok(U256::from_big_endian(&length_value)
        .try_into()
        .map_err(|_| Error::DataError("Invalid array length"))?)
}

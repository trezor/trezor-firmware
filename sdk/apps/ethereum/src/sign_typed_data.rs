use crate::{
    alloc_types::{BTreeMap, BTreeSet, String, ToString, Vec, vec},
    definitions::Definitions,
    helpers::address_from_bytes,
    layout::{
        confirm_empty_typed_message, confirm_message_hash, confirm_typed_data_final,
        confirm_typed_value, require_confirm_address, should_show_array, should_show_domain,
        should_show_struct,
    },
    paths::Bip32Path,
    proto::{
        ethereum::{
            SignTypedData, TypedDataSignature, TypedDataStructAck, TypedDataStructRequest,
            TypedDataValueAck, TypedDataValueRequest,
            typed_data_struct_ack::{DataType, FieldType},
        },
        messages::MessageType,
    },
};
use crate::{helpers::get_type_name, uformat, wire_request};
use primitive_types::U256;
use trezor_app_sdk::{
    Error, Result, ResultExt,
    crypto::{self, Hasher},
    ui, unwrap,
};

/// Ethereum uses Bitcoin xpub format
pub fn sign_typed_data(msg: SignTypedData) -> Result<TypedDataSignature> {
    let dp = Bip32Path::from_slice(&msg.address_n);
    let (encoded_network, encoded_token) = match &msg.definitions {
        Some(def) => (def.encoded_network.as_deref(), def.encoded_token.as_deref()),
        None => (None, None),
    };

    let slip44 = dp.slip44();
    let definitions = Definitions::from_encoded(encoded_network, encoded_token, None, slip44)?;

    crypto::verify_derivation_path(dp.as_slice(), encoded_network, encoded_token, None)?;

    let address_bytes =
        crypto::get_eth_pubkey_hash(dp.as_ref(), encoded_network, encoded_token, None)?;

    // Display address so user can validate it
    require_confirm_address(&address_bytes, None, None, None, None, None)?;

    let metamask_v4_compat = msg.metamask_v4_compat.unwrap_or(true);
    let show_message_hash = msg.show_message_hash.as_deref();

    let data_hash =
        generate_typed_data_hash(&msg.primary_type, metamask_v4_compat, show_message_hash)?;

    let mut signature = crypto::sign_typed_hash(
        dp.as_ref(),
        &data_hash,
        encoded_network,
        encoded_token,
        None,
        true,
    )?;

    signature.rotate_left(1);

    let sig = TypedDataSignature {
        signature: signature.to_vec(),
        address: address_from_bytes(&address_bytes, Some(definitions.network()))
            .context("Failed to convert bytes to address")?,
    };

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
            Some(tr!("ethereum__title_confirm_message")),
            Some(tr!("ethereum__show_full_message")),
        )?;
        ui::init_progress(
            None,
            Some(tr!("progress__loading_transaction")),
            false,
            false,
        )?;
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
        if show_message_hash != message_hash {
            return Err(Error::DataError("Message hash mismatch"));
        }

        confirm_message_hash(&message_hash)?;
    }

    confirm_typed_data_final()?;

    let mut hasher = crypto::Keccak256::new(None);
    hasher.update(b"\x19\x01");
    hasher.update(&domain_separator);
    hasher.update(&message_hash);
    Ok(hasher.digest())
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
            primary_type: primary_type.into(),
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
            validate_field_type(member_type)?;
            while member_type.data_type == DataType::Array as i32 {
                if let Some(entry_type) = &member_type.entry_type {
                    member_type = entry_type;
                } else {
                    return Err(Error::DataError("Missing member type"))?;
                }
            }
            if member_type.data_type == DataType::Struct as i32 {
                if let Some(struct_name) = &member_type.struct_name {
                    if !self.types.contains_key(struct_name) {
                        self._collect_types::<F>(struct_name, None)?;
                    }
                } else {
                    return Err(Error::DataError("Missing struct name"))?;
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
        let mut hasher = crypto::Keccak256::new(None);

        self.hash_type(&mut hasher, primary_type)?;

        self.get_and_encode_data(
            &mut hasher,
            primary_type,
            member_value_path,
            show_data,
            parent_objects,
            map_progress,
        )?;

        Ok(hasher.digest())
    }

    /// Gradually fetch data from client and encode the whole struct.
    ///
    /// SPEC:
    /// The encoding of a struct instance is enc(value₁) ‖ enc(value₂) ‖ … ‖ enc(valueₙ),
    /// i.e. the concatenation of the encoded member values in the order that they appear in the type.
    /// Each encoded member value is exactly 32-byte long.
    fn get_and_encode_data<F, H: Hasher>(
        &self,
        hasher: &mut H,
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
                    hasher.update(&hash);
                } else {
                    return Err(Error::DataError("Missing struct name for struct field"))?;
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
                    let mut arr_w = crypto::Keccak256::new(None);
                    let mut el_member_path = member_value_path.to_vec();
                    el_member_path.push(0);
                    for idx in 0..array_size {
                        // we can unwrap because the vector is never empty
                        *unwrap!(el_member_path.last_mut()) = idx;
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
                                    arr_w.update(&hash_struct);
                                } else {
                                    self.get_and_encode_data::<F, _>(
                                        &mut arr_w,
                                        struct_name,
                                        &el_member_path,
                                        show_array,
                                        &current_parent_objects,
                                        None,
                                    )?;
                                }
                            } else {
                                return Err(Error::DataError(
                                    "Missing entry type for array field",
                                ))?;
                            }
                        } else {
                            let value = get_value(entry_type, &el_member_path)?;
                            encode_field(&mut arr_w, entry_type, &value)?;
                            if show_array {
                                confirm_typed_value(
                                    field_name,
                                    &value,
                                    parent_objects,
                                    entry_type,
                                    Some(idx),
                                )?
                            }
                        }
                    }
                    let hash = arr_w.digest();
                    hasher.update(&hash);
                } else {
                    return Err(Error::DataError("Missing entry type for array field"))?;
                }
            } else {
                let value = get_value(field_type, &member_value_path)?;
                encode_field(hasher, field_type, &value)?;
                if show_data {
                    confirm_typed_value(field_name, &value, parent_objects, field_type, None)?
                }
            }
        }
        Ok(())
    }

    fn hash_type<H: Hasher>(&self, hasher: &mut H, primary_type: &str) -> Result<()> {
        let mut hasher_inner = crypto::Keccak256::new(Some(&self.encode_type(primary_type)?));
        hasher.update(&hasher_inner.digest());
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
        if let Some(s) = size
            && !(1..=32).contains(&s)
        {
            return Err(Error::DataError("Invalid bytes size"));
        }
    } else if data_type == DataType::Uint as i32 || data_type == DataType::Int as i32 {
        if let Some(s) = size {
            if !(1..=32).contains(&s) {
                return Err(Error::DataError("Invalid integer size"));
            }
        } else {
            return Err(Error::DataError("Missing integer size"));
        }
    } else if (data_type == DataType::String as i32
        || data_type == DataType::Bool as i32
        || data_type == DataType::Address as i32)
        && size.is_some()
    {
        return Err(Error::DataError("Unexpected size"));
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
        member_path: member_value_path.to_vec(),
    };

    let res: TypedDataValueAck = wire_request(&req, MessageType::TypedDataValueRequest)
        .context("Failed to get value from client")?;
    let value = res.value;

    validate_value(field, &value)?;
    Ok(value)
}

/// Make sure the byte data we receive are not corrupted or incorrect.
///
/// Return an error if encountering a problem, so clients are notified.
fn validate_value(field: &FieldType, value: &[u8]) -> Result<()> {
    // Size check
    if let Some(size) = field.size
        && value.len() != size as usize
    {
        return Err(Error::DataError("Invalid value size"));
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
///
/// Dynamic types:
/// - Bytes and string are encoded as a keccak256 hash of their contents
///
/// Reference types:
/// - Array values are encoded as the keccak256 hash of the concatenated
///   encodeData of their contents
/// - Struct values are encoded recursively as hashStruct(value)
fn encode_field<H: Hasher>(h: &mut H, field: &FieldType, value: &[u8]) -> Result<()> {
    if field.data_type == DataType::Bytes as i32 {
        if let Some(_size) = field.size {
            // write_rightpad32
            h.update(&rightpad32(value)?);
        } else {
            let mut hasher_inner = crypto::Keccak256::new(Some(value));
            h.update(&hasher_inner.digest());
        };
    } else if field.data_type == DataType::String as i32 {
        let mut hasher_inner = crypto::Keccak256::new(Some(value));
        h.update(&hasher_inner.digest());
    } else if field.data_type == DataType::Int as i32 {
        h.update(&leftpad32(value, true)?);
    } else if field.data_type == DataType::Uint as i32
        || field.data_type == DataType::Bool as i32
        || field.data_type == DataType::Address as i32
    {
        h.update(&leftpad32(value, false)?);
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

    U256::from_big_endian(&length_value)
        .try_into()
        .map_err(|_| Error::DataError("Invalid array length"))
}

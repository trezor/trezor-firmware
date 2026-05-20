use crate::{
    alloc_types::{String, Vec},
    definitions::Definitions,
    payment_request::PaymentRequestVerifier,
    proto::ethereum::Definitions as EthereumDefinitions,
};
use primitive_types::U256;
use trezor_app_sdk::{Result, ui::Property};

pub enum Value {
    Int(U256),
    Bytes(Vec<u8>),
    Bool(bool),
    Str(String),
    None,
    List(Vec<Value>),
    Tuple(Vec<Value>),
}

// Field formatters: https://eips.ethereum.org/EIPS/eip-7730#field-formats
trait FieldFormatter {
    fn format(&self, value: &Value) -> String;
}

// TODO: implement
pub(crate) fn try_confirm<'a>(
    _data: &[u8],
    _address_bytes: &[u8],
    // _msg: &SignTx,
    _chain_id: u64,
    _definitions: Option<&EthereumDefinitions>,
    _defs: &Definitions,
    _maximum_fee: &str,
    _fee_items: &[Property<'a>],
    _payment_request_verifier: Option<&PaymentRequestVerifier>,
) -> Result<bool> {
    Ok(false)
}

// #[inline(never)]
// /// Sanity check to make sure unused data is zeroed out.
// fn check_padding_zero(raw: &[u8], used_bytes: usize) -> Result<()> {
//     assert!(used_bytes <= 32);
//     if raw.len() < 32 {
//         return Err(Error::DataError("ClearSigningError::OutOfBounds"));
//     }
//     let pad = 32usize - used_bytes;
//     if raw[pad..].iter().any(|b| *b != 0) {
//         return Err(Error::DataError("ClearSigningError"));
//     }
//     Ok(())
// }

// #[inline(never)]
// fn parse_address(raw: &[u8]) -> Result<Value> {
//     const ADDR_BYTES: usize = 20;
//     if raw.len() < 32 {
//         return Err(ClearSigningError::OutOfBounds);
//     }
//     check_padding_zero(raw, ADDR_BYTES, ClearSigningError::DirtyAddress)?;
//     Ok(Value::Bytes(raw[32 - ADDR_BYTES..32].to_vec()))
// }

// #[inline(never)]
// fn parse_uint256(raw: &[u8]) -> Result<Value> {
//     if raw.len() < 32 {
//         return Err(ClearSigningError::OutOfBounds);
//     }
//     Ok(Value::Int(U256::from_big_endian(&raw[..32])))
// }

// #[inline(never)]
// fn parse_uint_n(raw: &[u8], bit_width: usize) -> Result<Value> {
//     let byte_width = bit_width / 8;
//     check_padding_zero(raw, byte_width, ClearSigningError::ValueOverflow)?;
//     parse_uint256(raw)
// }

// #[inline(never)]
// fn parse_bool(raw: &[u8]) -> Result<Value> {
//     let v = parse_uint256(raw)?;
//     let Value::Int(x) = v else {
//         return Err(ClearSigningError::InvalidFormatDefinition);
//     };
//     if x == U256::zero() {
//         Ok(Value::Bool(false))
//     } else if x == U256::one() {
//         Ok(Value::Bool(true))
//     } else {
//         Err(ClearSigningError::ValueOverflow)
//     }
// }

// #[inline(never)]
// fn parse_bytes(raw: &[u8]) -> Result<Value> {
//     Ok(Value::Bytes(raw.to_vec()))
// }

// #[inline(never)]
// fn parse_string(raw: &[u8]) -> Result<Value> {
//     let s = core::str::from_utf8(raw).map_err(|_| ClearSigningError::InvalidFunctionCall)?;
//     Ok(Value::Str(s.to_string()))
// }

// #[inline(never)]
// fn parse_uint256_array(raw: &[u8]) -> Result<Value> {
//     if raw.len() % 32 != 0 {
//         return Err(ClearSigningError::InvalidFunctionCall);
//     }
//     let mut out = Vec::with_capacity(raw.len() / 32);
//     for chunk in raw.chunks_exact(32) {
//         out.push(parse_uint256(chunk)?);
//     }
//     Ok(Value::List(out))
// }

// #[inline(never)]
// fn parse_by_type(t: AbiType, raw: &[u8]) -> Result<Value> {
//     match t {
//         AbiType::Address => parse_address(raw),
//         AbiType::Bytes => parse_bytes(raw),
//         AbiType::String => parse_string(raw),
//         AbiType::Uint256 => parse_uint256(raw),
//         AbiType::Uint248 => parse_uint_n(raw, 248),
//         AbiType::Uint160 => parse_uint_n(raw, 160),
//         AbiType::Uint128 => parse_uint_n(raw, 128),
//         AbiType::Uint120 => parse_uint_n(raw, 120),
//         AbiType::Uint112 => parse_uint_n(raw, 112),
//         AbiType::Uint96 => parse_uint_n(raw, 96),
//         AbiType::Uint72 => parse_uint_n(raw, 72),
//         AbiType::Uint64 => parse_uint_n(raw, 64),
//         AbiType::Uint48 => parse_uint_n(raw, 48),
//         AbiType::Uint40 => parse_uint_n(raw, 40),
//         AbiType::Uint32 => parse_uint_n(raw, 32),
//         AbiType::Uint24 => parse_uint_n(raw, 24),
//         AbiType::Uint16 => parse_uint_n(raw, 16),
//         AbiType::Uint8 => parse_uint_n(raw, 8),
//         AbiType::Bool => parse_bool(raw),
//     }
// }

// #[derive(Debug, Clone, Copy, PartialEq, Eq)]
// pub enum ContainerPath {
//     From = 1,
//     Value = 2,
// }

// #[derive(Debug, Clone, PartialEq, Eq)]
// pub enum PathStep {
//     Index(usize),
//     SliceFrom(usize),
//     Slice(usize, usize),
// }

// pub enum Path {
//     Container(ContainerPath),
//     Steps(Vec<PathStep>),
// }

// pub enum AbiValue {
//     Atomic(AbiType),
//     Dynamic(AbiType),
//     Tuple {
//         fields: Vec<LeafValue>,
//         is_dynamic: bool,
//     },
//     Array {
//         element: Box<AbiValue>,
//     },
// }

// #[derive(Debug, Clone)]
// pub enum LeafValue {
//     Atomic(AbiType),
//     Dynamic(AbiType),
// }

// impl LeafValue {
//     #[inline(never)]
//     fn is_dynamic(&self) -> bool {
//         matches!(self, LeafValue::Dynamic(_))
//     }

//     #[inline(never)]
//     fn parse_leaf(&self, raw: &[u8]) -> Result<Value> {
//         match self {
//             LeafValue::Atomic(t) | LeafValue::Dynamic(t) => parse_by_type(*t, raw),
//         }
//     }
// }

// impl AbiValue {
//     #[inline(never)]
//     pub fn parse(&self, raw_data: &[u8], offset: usize) -> Result<(Value, usize)> {
//         match self {
//             AbiValue::Atomic(t) => {
//                 let end = offset
//                     .checked_add(32)
//                     .ok_or(ClearSigningError::OutOfBounds)?;
//                 if end > raw_data.len() {
//                     return Err(ClearSigningError::OutOfBounds);
//                 }
//                 Ok((parse_by_type(*t, &raw_data[offset..end])?, 32))
//             }
//             AbiValue::Dynamic(t) => {
//                 let ptr_end = offset
//                     .checked_add(32)
//                     .ok_or(ClearSigningError::OutOfBounds)?;
//                 if ptr_end > raw_data.len() {
//                     return Err(ClearSigningError::OutOfBounds);
//                 }
//                 let pointer = U256::from_big_endian(&raw_data[offset..ptr_end]).as_usize();
//                 let len_end = pointer
//                     .checked_add(32)
//                     .ok_or(ClearSigningError::OutOfBounds)?;
//                 if len_end > raw_data.len() {
//                     return Err(ClearSigningError::OutOfBounds);
//                 }
//                 let length = U256::from_big_endian(&raw_data[pointer..len_end]).as_usize();
//                 let data_start = len_end;
//                 let data_end = data_start
//                     .checked_add(length)
//                     .ok_or(ClearSigningError::OutOfBounds)?;
//                 if data_end > raw_data.len() {
//                     return Err(ClearSigningError::OutOfBounds);
//                 }
//                 Ok((parse_by_type(*t, &raw_data[data_start..data_end])?, 32))
//             }
//             AbiValue::Tuple { fields, is_dynamic } => {
//                 let (base_offset, consumed) = if !*is_dynamic {
//                     (offset, fields.len() * 32)
//                 } else {
//                     let ptr_end = offset
//                         .checked_add(32)
//                         .ok_or(ClearSigningError::OutOfBounds)?;
//                     if ptr_end > raw_data.len() {
//                         return Err(ClearSigningError::OutOfBounds);
//                     }
//                     (
//                         U256::from_big_endian(&raw_data[offset..ptr_end]).as_usize(),
//                         32,
//                     )
//                 };

//                 let static_size = fields.len() * 32;
//                 if base_offset + static_size > raw_data.len() {
//                     return Err(ClearSigningError::OutOfBounds);
//                 }

//                 let mut out = vec![Value::None; fields.len()];
//                 for (i, parser) in fields.iter().enumerate() {
//                     let head = base_offset + i * 32;
//                     let head_end = head + 32;
//                     let raw_field = &raw_data[head..head_end];

//                     if !parser.is_dynamic() {
//                         out[i] = parser.parse_leaf(raw_field)?;
//                     } else {
//                         let rel_ptr = U256::from_big_endian(raw_field).as_usize();
//                         let field_ptr = base_offset + rel_ptr;
//                         if field_ptr + 32 > raw_data.len() {
//                             return Err(ClearSigningError::OutOfBounds);
//                         }
//                         let len =
//                             U256::from_big_endian(&raw_data[field_ptr..field_ptr + 32]).as_usize();
//                         let start = field_ptr + 32;
//                         let end = start + len;
//                         if end > raw_data.len() {
//                             return Err(ClearSigningError::OutOfBounds);
//                         }
//                         out[i] = parser.parse_leaf(&raw_data[start..end])?;
//                     }
//                 }

//                 Ok((Value::Tuple(out), consumed))
//             }
//             AbiValue::Array { element } => {
//                 let ptr_end = offset
//                     .checked_add(32)
//                     .ok_or(ClearSigningError::OutOfBounds)?;
//                 if ptr_end > raw_data.len() {
//                     return Err(ClearSigningError::OutOfBounds);
//                 }
//                 let array_ptr = U256::from_big_endian(&raw_data[offset..ptr_end]).as_usize();
//                 if array_ptr + 32 > raw_data.len() {
//                     return Err(ClearSigningError::OutOfBounds);
//                 }
//                 let array_len =
//                     U256::from_big_endian(&raw_data[array_ptr..array_ptr + 32]).as_usize();
//                 let heads_end = array_ptr + 32 + array_len * 32;
//                 if heads_end > raw_data.len() {
//                     return Err(ClearSigningError::OutOfBounds);
//                 }

//                 let mut values = Vec::with_capacity(array_len);
//                 for i in 0..array_len {
//                     let p = array_ptr + 32 + i * 32;
//                     if p + 32 > raw_data.len() {
//                         return Err(ClearSigningError::OutOfBounds);
//                     }
//                     let (v, _) = match element.as_ref() {
//                         AbiValue::Atomic(_) => element.parse(raw_data, p)?,
//                         _ => {
//                             let rel_ptr = U256::from_big_endian(&raw_data[p..p + 32]).as_usize();
//                             let abs_ptr = array_ptr + 32 + rel_ptr;
//                             element.parse(raw_data, abs_ptr)?
//                         }
//                     };
//                     values.push(v);
//                 }

//                 Ok((Value::List(values), 32))
//             }
//         }
//     }
// }

//  https://eips.ethereum.org/EIPS/eip-7730#context-section
// struct BindingContext {
//     pub deployments: Vec<(u64, Vec<u8>)>,
// }

// impl BindingContext {
//     pub fn matches(&self, chain_id: u64, address: &[u8]) -> bool {
//         self.deployments
//             .iter()
//             .any(|(c, a)| *c == chain_id && a.as_slice() == address)
//     }
// }

// pub struct DisplayFormat {
//     pub binding_context: Option<BindingContext>,
//     pub func_sig: [u8; SC_FUNC_SIG_BYTES],
//     pub intent: String,
//     pub parameter_definitions: Vec<AbiValue>,
//     pub field_definitions: Vec<FieldDefinition>,
// }

// impl DisplayFormat {
//     pub(crate) fn parse(
//         &self,
//         _calldata: &[u8],
//         _dp: &Bip32Path,
//         _value: U256,
//         _definitions: &Definitions,
//         _token: &TokenInfo,
//     ) -> Result<(
//         Vec<String>,
//         Vec<(Property, Option<TokenInfo>, Option<Vec<u8>>)>,
//     )> {
//         // TODO: implement
//         Err(Error::Cancelled)
//     }

//     #[inline(never)]
//     pub fn matches_context(&self, chain_id: u64, address: &[u8]) -> bool {
//         self.binding_context
//             .as_ref()
//             .map(|bc| bc.matches(chain_id, address))
//             .unwrap_or(true)
//     }

//     #[inline(never)]
//     pub fn parse_parameters(&self, calldata: &[u8]) -> Result<Vec<Value>> {
//         let mut out = Vec::with_capacity(self.parameter_definitions.len());
//         let mut offset = 0usize;
//         for def in &self.parameter_definitions {
//             let (value, consumed) = def.parse(calldata, offset)?;
//             out.push(value);
//             offset += consumed;
//         }
//         Ok(out)
//     }
// }

// // Optional helper, mirroring Python DYNAMIC_DATA_PARSERS behavior when needed.
// #[inline(never)]
// pub fn is_dynamic_leaf_type(t: AbiType) -> bool {
//     matches!(t, AbiType::Bytes | AbiType::String) || t == AbiType::Uint256 // for uint256[] parser parity
// }

// #[inline(never)]
// pub fn format_unit(value: U256, decimals: u32, base: &str, prefix: bool) -> String {
//     // Minimal port of UnitFormatter behavior.
//     // TODO: replace with exact app formatter rules if you need byte-for-byte parity with Micropython.
//     let denom = U256::from(10u64).pow(U256::from(decimals));
//     let int = value / denom;
//     let frac = value % denom;

//     if !prefix || value.is_zero() {
//         if frac.is_zero() {
//             return format!("{int}{base}");
//         }
//         return format!("{int}.{frac}{base}");
//     }

//     // simplified SI prefix handling
//     let mut scaled = int;
//     let mut exp: i32 = 0;
//     while scaled >= U256::from(1000u64) && exp < 12 {
//         scaled /= U256::from(1000u64);
//         exp += 3;
//     }

//     let p = match exp {
//         12 => "T",
//         9 => "G",
//         6 => "M",
//         3 => "k",
//         0 => "",
//         -3 => "m",
//         _ => "",
//     };
//     format!("{scaled}{p}{base}")
// }

// fn _handle_transfer(
//     calldata: &[u8],
//     display_format: &DisplayFormat,
//     address_bytes: &[u8],
//     msg: &SignTx,
//     definitions: &Definitions,
//     token: &TokenInfo,
//     maximum_fee: &str,
//     fee_items: &[Property],
//     payment_request_verifier: Option<&PaymentRequestVerifier>,
// ) -> Result<()> {
//     let dp = Bip32Path::from_slice(&msg.address_n);

//     assert!(msg.value.is_some());
//     let value = U256::from_big_endian(unwrap!(msg.value.as_deref()));

//     let (args, fields) = display_format.parse(calldata, &dp, value, definitions, token)?;

//     assert!(args.len() == 2);
//     assert!(fields.len() == 2);

//     let prop1 = fields[0].0;
//     assert!(prop1.key.as_str() == "To");

//     // TODO: let arg1_raw_value = args[1];
//     let arg1_raw_value = 0.into();

//     // assert isinstance(arg1_raw_value, int)
//     let prop2 = fields[1].0;
//     assert!(prop2.key.as_str() == "Amount");

//     if let Some(payment_request_verifier) = payment_request_verifier {
//         // SLIP-24 payment requests for ERC-20 token transfers

//         assert!(msg.payment_req.is_some());

//         payment_request_verifier.add_output(arg1_raw_value, prop1.value.as_str(), None)?;
//         payment_request_verifier.verify()?;
//         require_confirm_payment_request(
//             prop1.value.as_str(),
//             unwrap!(msg.payment_req.as_ref()),
//             &dp,
//             maximum_fee,
//             fee_items,
//             msg.chain_id,
//             definitions.network(),
//             Some(token),
//             &address_from_bytes(address_bytes, Some(definitions.network())),
//         )?;
//     } else {
//         require_confirm_tx(
//             Some(prop1.value.as_str()),
//             value,
//             address_bytes,
//             msg.address_n,
//             maximum_fee,
//             fee_items,
//             token,
//             true,
//             msg.chunkify,
//         )?;
//     }

//     Ok(())
// }

// fn handle_generic_ui(
//     calldata: &[u8],
//     display_format: &DisplayFormat,
//     msg: &SignTx,
//     definitions: &Definitions,
//     token: &TokenInfo,
//     maximum_fee: &str,
// ) -> Result<()> {

//     let (_, fields) = display_format.parse(
//         calldata, msg.address_n, msg.value, definitions, token
//     )?;

//     let mut properties_to_confirm = Vec::new();

//     for field, actual_token, actual_token_address in fields:
//         properties_to_confirm.append(field)
//         if actual_token is tokens.UNKNOWN_TOKEN:
//             assert actual_token_address is not None
//             token_address_str = address_from_bytes(
//                 actual_token_address, definitions.network
//             )
//             token_address_property: StrPropertyType = (
//                 TR.ethereum__token_contract,
//                 token_address_str,
//                 None,
//             )
//             properties_to_confirm.append(token_address_property)

//     recipient_str = KNOWN_ADDRESSES.get(bytes_from_address(msg.to), msg.to)

//     require_confirm_clear_signing(
//         recipient_str, display_format.intent, properties_to_confirm, maximum_fee
//     )?;
//     Ok(())
// }

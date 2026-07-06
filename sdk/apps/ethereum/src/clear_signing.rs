use crate::{
    alloc_types::{Box, String, ToString, Vec, vec},
    clear_signing_definitions::{
        SC_FUNC_APPROVE_REVOKE_AMOUNT, get_all_display_formats, get_approve_display_format,
        get_transfer_display_format,
    },
    definitions::{self, decode_definition},
    helpers::bytes_from_address,
    layout::{
        require_confirm_approve, require_confirm_clear_signing, require_confirm_payment_request,
        require_confirm_tx,
    },
    paths::Bip32Path,
    payment_request::PaymentRequestVerifier,
    proto::{
        common::PaymentRequest,
        definitions::{
            AbiType, AbiValueInfo, DisplayFormatInfo, Erc7730FieldFormatterType, Erc7730FieldInfo,
            Erc7730Path,
        },
        ethereum::{self, DefinitionAck, DefinitionRequest},
        messages::MessageType,
    },
    sc_constants::{SC_FUNC_SIG_BYTES, get_approve_known_address},
    strutil, uformat, wire_request,
    yielding_vaults::{lookup_vault, unknown_vault},
};
use primitive_types::U256;
use trezor_app_sdk::{Error, Result, ui::Property};

pub enum ClearSigningError {
    InvalidFunctionCall,
    ValueOverflow,
    DirtyAddress,
    OutOfBounds,
    InvalidFormatDefinition,
    NotImplemented,
}

impl From<ClearSigningError> for Error {
    fn from(e: ClearSigningError) -> Self {
        Error::DataError(match e {
            ClearSigningError::InvalidFunctionCall => "clear signing: invalid function call",
            ClearSigningError::ValueOverflow => "clear signing: value overflow",
            ClearSigningError::DirtyAddress => "clear signing: dirty address",
            ClearSigningError::OutOfBounds => "clear signing: out of bounds",
            ClearSigningError::InvalidFormatDefinition => {
                "clear signing: invalid format definition"
            }
            ClearSigningError::NotImplemented => "clear signing: not implemented",
        })
    }
}

/// Sanity check to make sure unused data is zeroed out.
fn check_padding_zero(raw: &[u8], used_bytes: usize) -> Result<()> {
    if used_bytes > 32 {
        return Err(Error::from(ClearSigningError::InvalidFormatDefinition));
    }
    if raw.len() < 32 {
        return Err(Error::from(ClearSigningError::OutOfBounds));
    }
    let pad = 32usize - used_bytes;
    if raw[..pad].iter().any(|b| *b != 0) {
        return Err(Error::from(ClearSigningError::InvalidFormatDefinition));
    }
    Ok(())
}

pub fn parse_address(raw: &[u8]) -> Result<Vec<u8>> {
    const ZERO_PADDING: usize = 20;
    if raw.len() < 32 {
        return Err(Error::from(ClearSigningError::OutOfBounds));
    }
    check_padding_zero(raw, ZERO_PADDING)?;
    Ok(raw[32 - ZERO_PADDING..].to_vec())
}

// ---- Parsers ----------------------------------------------------------------

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum AtomicType {
    Address,
    Uint256,
    Uint248,
    Uint160,
    Uint128,
    Uint120,
    Uint112,
    Uint96,
    Uint72,
    Uint64,
    Uint48,
    Uint40,
    Uint32,
    Uint24,
    Uint16,
    Uint8,
    Bool,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DynamicType {
    Bytes,
    String,
}

fn atomic_type_from_proto(t: i32) -> Result<AtomicType> {
    match t {
        x if x == AbiType::AbiAddress as i32 => Ok(AtomicType::Address),
        x if x == AbiType::AbiUint256 as i32 => Ok(AtomicType::Uint256),
        x if x == AbiType::AbiUint248 as i32 => Ok(AtomicType::Uint248),
        x if x == AbiType::AbiUint160 as i32 => Ok(AtomicType::Uint160),
        x if x == AbiType::AbiUint128 as i32 => Ok(AtomicType::Uint128),
        x if x == AbiType::AbiUint120 as i32 => Ok(AtomicType::Uint120),
        x if x == AbiType::AbiUint112 as i32 => Ok(AtomicType::Uint112),
        x if x == AbiType::AbiUint96 as i32 => Ok(AtomicType::Uint96),
        x if x == AbiType::AbiUint72 as i32 => Ok(AtomicType::Uint72),
        x if x == AbiType::AbiUint64 as i32 => Ok(AtomicType::Uint64),
        x if x == AbiType::AbiUint48 as i32 => Ok(AtomicType::Uint48),
        x if x == AbiType::AbiUint40 as i32 => Ok(AtomicType::Uint40),
        x if x == AbiType::AbiUint32 as i32 => Ok(AtomicType::Uint32),
        x if x == AbiType::AbiUint24 as i32 => Ok(AtomicType::Uint24),
        x if x == AbiType::AbiUint16 as i32 => Ok(AtomicType::Uint16),
        x if x == AbiType::AbiUint8 as i32 => Ok(AtomicType::Uint8),
        x if x == AbiType::AbiBool as i32 => Ok(AtomicType::Bool),
        _ => Err(Error::from(ClearSigningError::InvalidFormatDefinition))?,
    }
}

fn dynamic_type_from_proto(t: i32) -> Result<DynamicType> {
    match t {
        x if x == AbiType::AbiBytes as i32 => Ok(DynamicType::Bytes),
        x if x == AbiType::AbiString as i32 => Ok(DynamicType::String),
        _ => Err(Error::from(ClearSigningError::InvalidFormatDefinition)),
    }
}

fn get_leaf_parser(info: &AbiValueInfo) -> Result<LeafParser> {
    if let Some(t) = info.atomic {
        return Ok(LeafParser::Atomic(atomic_type_from_proto(t)?));
    }
    if let Some(t) = info.dynamic {
        return Ok(LeafParser::Dynamic(dynamic_type_from_proto(t)?));
    }
    Err(Error::from(ClearSigningError::InvalidFormatDefinition))
}

/// Leaf parser: either atomic (32-byte) or dynamic (variable-length).
#[derive(Debug, Clone)]
pub enum LeafParser {
    Atomic(AtomicType),
    Dynamic(DynamicType),
}

// ---- ABIValue ---------------------------------------------------------------

/// Mirrors Python's ABIValue / Atomic / Dynamic / Tuple / Array hierarchy
/// as a closed enum — no trait dispatch needed.
#[derive(Debug)]
pub enum AbiValue {
    /// 32-byte fixed-size value
    Atomic(AtomicType),
    /// Variable-length value accessed via pointer
    Dynamic(DynamicType),
    /// Struct / tuple of leaf fields
    Tuple {
        fields: Vec<LeafParser>,
        is_dynamic: bool,
    },
    /// Array of elements (Array-of-Array not supported)
    Array(Box<AbiValue>),
}

impl AbiValue {
    pub fn from_proto(info: &AbiValueInfo) -> Result<Self> {
        if let Some(t) = info.atomic {
            return Ok(AbiValue::Atomic(atomic_type_from_proto(t)?));
        }

        if let Some(t) = info.dynamic {
            return Ok(AbiValue::Dynamic(dynamic_type_from_proto(t)?));
        }

        if let Some(ref tup) = info.tuple {
            let fields = tup
                .fields
                .iter()
                .map(get_leaf_parser)
                .collect::<Result<Vec<_>>>()?;
            return Ok(AbiValue::Tuple {
                fields,
                is_dynamic: tup.is_dynamic,
            });
        }

        if let Some(ref element) = info.array {
            if let Some(t) = element.atomic {
                return Ok(AbiValue::Array(Box::new(AbiValue::Atomic(
                    atomic_type_from_proto(t)?,
                ))));
            }
            if let Some(t) = element.dynamic {
                return Ok(AbiValue::Array(Box::new(AbiValue::Dynamic(
                    dynamic_type_from_proto(t)?,
                ))));
            }
            if let Some(ref tup) = element.tuple {
                let fields = tup
                    .fields
                    .iter()
                    .map(get_leaf_parser)
                    .collect::<Result<Vec<_>>>()?;
                // Tuples inside Arrays are always parsed as static
                return Ok(AbiValue::Array(Box::new(AbiValue::Tuple {
                    fields,
                    is_dynamic: false,
                })));
            }
            // Array of arrays not supported
            return Err(Error::from(ClearSigningError::InvalidFormatDefinition));
        }

        Err(Error::from(ClearSigningError::InvalidFormatDefinition))
    }
}

// ---- ContainerPath ----------------------------------------------------------

#[derive(Debug, Clone)]
pub enum ContainerPath {
    From = 1,
    Value = 2,
    To = 3,
}

// ---- Path -------------------------------------------------------------------

#[derive(Debug, Clone)]
pub enum PathStep {
    Index(usize),
    SliceFrom(usize),
    Slice(usize, usize),
}

#[derive(Debug, Clone)]
pub enum Path {
    Container(ContainerPath),
    Fields(Vec<PathStep>),
}

impl Path {
    fn decode(p: &Erc7730Path) -> Result<Self> {
        if let Some(container) = p.container_path {
            let cp = match container {
                1 => ContainerPath::From,
                2 => ContainerPath::Value,
                3 => ContainerPath::To,
                _ => return Err(Error::from(ClearSigningError::InvalidFormatDefinition))?,
            };
            return Ok(Path::Container(cp));
        }

        let steps = p
            .path
            .iter()
            .map(|&idx| PathStep::Index(idx as usize))
            .collect();
        Ok(Path::Fields(steps))
    }
}

// ---- Formatters -------------------------------------------------------------

#[derive(Debug)]
pub struct TokenAmountFormatterParams {
    pub token_path: Path,
    pub threshold: Option<U256>,
}

#[derive(Debug)]
pub struct UnitFormatterParams {
    pub decimals: u32,
    pub base: String,
    pub prefix: bool,
}

#[derive(Debug)]
pub enum FieldFormatter {
    AddressName,
    Amount,
    TokenAmount(TokenAmountFormatterParams),
    Unit(UnitFormatterParams),
}

// ---- FieldDefinition --------------------------------------------------------

#[derive(Debug)]
pub struct FieldDefinition {
    pub path: Path,
    pub label: String,
    pub formatter: FieldFormatter,
}

impl FieldDefinition {
    pub fn from_proto(info: &Erc7730FieldInfo) -> Result<Self> {
        let path = Path::decode(&info.path)?;

        let formatter = match info.formatter {
            i if i == Erc7730FieldFormatterType::AddressName as i32 => FieldFormatter::AddressName,
            i if i == Erc7730FieldFormatterType::Amount as i32 => FieldFormatter::Amount,
            i if i == Erc7730FieldFormatterType::TokenAmount as i32 => {
                let token_path = Path::decode(
                    info.token_path
                        .as_ref()
                        .ok_or(Error::from(ClearSigningError::InvalidFormatDefinition))?,
                )?;
                let threshold = info.threshold.as_ref().map(|b| U256::from_big_endian(b));
                FieldFormatter::TokenAmount(TokenAmountFormatterParams {
                    token_path,
                    threshold,
                })
            }
            i if i == Erc7730FieldFormatterType::Unit as i32 => {
                FieldFormatter::Unit(UnitFormatterParams {
                    decimals: info.decimals.unwrap_or(0),
                    base: info.base.clone().unwrap_or_default(),
                    prefix: info.prefix.unwrap_or(false),
                })
            }
            _ => return Err(Error::from(ClearSigningError::InvalidFormatDefinition))?,
        };

        Ok(FieldDefinition {
            path,
            label: info.label.clone(),
            formatter,
        })
    }
}

// ---- BindingContext ----------------------------------------------------------

#[derive(Debug)]
pub struct BindingContext {
    pub deployments: Vec<(u64, Vec<u8>)>, // (chain_id, address)
}

impl BindingContext {
    pub fn matches(&self, chain_id: u64, address: &[u8]) -> bool {
        self.deployments
            .iter()
            .any(|(cid, addr)| *cid == chain_id && addr == address)
    }
}

// ---- DisplayFormat ----------------------------------------------------------

pub struct DisplayFormat {
    pub binding_context: Option<BindingContext>,
    pub func_sig: [u8; 4],
    pub intent: String,
    pub parameter_definitions: Vec<AbiValue>,
    pub field_definitions: Vec<FieldDefinition>,
}

impl DisplayFormat {
    pub fn matches_context(&self, chain_id: u64, address: &[u8]) -> bool {
        match &self.binding_context {
            None => true,
            Some(ctx) => ctx.matches(chain_id, address),
        }
    }

    pub fn from_encoded(encoded: &[u8]) -> Result<Self> {
        let proto: DisplayFormatInfo = decode_definition::<DisplayFormatInfo>(encoded)
            .map_err(|_| Error::from(ClearSigningError::InvalidFormatDefinition))?;

        let func_sig: [u8; 4] = proto
            .func_sig
            .as_slice()
            .try_into()
            .map_err(|_| Error::from(ClearSigningError::InvalidFormatDefinition))?;

        Ok(DisplayFormat {
            binding_context: Some(BindingContext {
                deployments: vec![(proto.chain_id, proto.address)],
            }),
            func_sig,
            intent: proto.intent,
            parameter_definitions: proto
                .parameter_definitions
                .iter()
                .map(AbiValue::from_proto)
                .collect::<Result<_>>()?,
            field_definitions: proto
                .field_definitions
                .iter()
                .map(FieldDefinition::from_proto)
                .collect::<Result<_>>()?,
        })
    }
}

pub struct ParsedField {
    pub label: String,
    pub formatted: Option<String>,
    pub token: Option<Vec<u8>>, // token address bytes
    pub raw_value: Option<Vec<u8>>,
}

pub enum ParsedParameter {
    Address(Vec<u8>),
    Uint(U256),
    Bool(bool),
    Bytes(Vec<u8>),
    Tuple(Vec<ParsedParameter>),
    Array(Vec<ParsedParameter>),
}

impl DisplayFormat {
    pub fn parse_calldata(
        &self,
        calldata: &[u8],
        container: &ContainerValues,
        defs: &definitions::Definitions,
    ) -> Result<(Vec<ParsedParameter>, Vec<ParsedField>)> {
        // 1. Parse ABI parameters
        let mut parameters = Vec::new();
        let mut offset = 0;
        for param_def in &self.parameter_definitions {
            let (value, consumed) = parse_abi_value(param_def, calldata, offset)?;
            parameters.push(value);
            offset += consumed;
        }

        // 2. Format fields
        let mut fields = Vec::new();
        for field_def in &self.field_definitions {
            let raw = get_value_for_path(&field_def.path, &parameters, container)?;
            let (formatted, token) = format_field(&field_def.formatter, &raw, defs)?;
            fields.push(ParsedField {
                label: field_def.label.clone(),
                formatted,
                token,
                raw_value: Some(raw),
            });
        }

        Ok((parameters, fields))
    }
}

/// Holds values accessible via ContainerPath (@.from, @.value, @.to)
pub struct ContainerValues<'a> {
    pub from: Option<&'a str>, // sender account string
    pub value: U256,           // tx value
    pub to: &'a [u8],          // recipient address bytes
}

fn get_value_for_path(
    path: &Path,
    parameters: &[ParsedParameter],
    container: &ContainerValues,
) -> Result<Vec<u8>> {
    match path {
        Path::Container(cp) => match cp {
            ContainerPath::From => Ok(container.from.unwrap_or("").as_bytes().to_vec()),
            ContainerPath::Value => Ok(container.value.to_big_endian().to_vec()),
            ContainerPath::To => Ok(container.to.to_vec()),
        },
        Path::Fields(steps) => {
            if steps.is_empty() {
                return Err(Error::from(ClearSigningError::InvalidFormatDefinition))?;
            }
            walk_path(steps, parameters)
        }
    }
}

fn walk_path(steps: &[PathStep], params: &[ParsedParameter]) -> Result<Vec<u8>> {
    let mut current: &ParsedParameter = match steps.first() {
        Some(PathStep::Index(i)) => params
            .get(*i)
            .ok_or(Error::from(ClearSigningError::InvalidFormatDefinition))?,
        _ => return Err(Error::from(ClearSigningError::InvalidFormatDefinition))?,
    };

    for step in &steps[1..] {
        match (step, current) {
            (PathStep::Index(i), ParsedParameter::Tuple(fields)) => {
                current = fields
                    .get(*i)
                    .ok_or(Error::from(ClearSigningError::InvalidFormatDefinition))?;
            }
            (PathStep::Index(i), ParsedParameter::Array(items)) => {
                current = items
                    .get(*i)
                    .ok_or(Error::from(ClearSigningError::InvalidFormatDefinition))?;
            }
            _ => return Err(Error::from(ClearSigningError::InvalidFormatDefinition))?,
        }
    }

    encode_parsed_parameter(current)
}

fn encode_parsed_parameter(p: &ParsedParameter) -> Result<Vec<u8>> {
    match p {
        ParsedParameter::Address(b) => Ok(b.clone()),
        ParsedParameter::Uint(u) => Ok(u.to_big_endian().to_vec()),
        ParsedParameter::Bool(b) => Ok(vec![*b as u8]),
        ParsedParameter::Bytes(b) => Ok(b.clone()),
        _ => Err(Error::from(ClearSigningError::InvalidFormatDefinition))?,
    }
}

fn format_field(
    formatter: &FieldFormatter,
    raw: &[u8],
    _defs: &definitions::Definitions,
) -> Result<(Option<String>, Option<Vec<u8>>)> {
    match formatter {
        FieldFormatter::AddressName => {
            let addr = strutil::hex_encode(raw)
                .map_err(|_| Error::DataError("Failed to hex-encode address"))?;
            Ok((Some(addr), None))
        }
        FieldFormatter::Amount => {
            let u = U256::from_big_endian(raw);
            Ok((Some(u.to_string()), None))
        }
        FieldFormatter::TokenAmount(params) => {
            // token address resolved at call site via token_path
            let u = U256::from_big_endian(raw);
            let above = params.threshold.is_some_and(|t| u >= t);
            if above {
                Ok((None, None)) // AboveThreshold — caller handles
            } else {
                Ok((Some(u.to_string()), None))
            }
        }
        FieldFormatter::Unit(params) => {
            let u = U256::from_big_endian(raw);
            let formatted = uformat!("{} {}", u.to_string().as_str(), params.base.as_str());
            Ok((Some(formatted), None))
        }
    }
}

fn parse_abi_value(
    abi: &AbiValue,
    calldata: &[u8],
    offset: usize,
) -> Result<(ParsedParameter, usize)> {
    match abi {
        AbiValue::Atomic(t) => {
            if offset + 32 > calldata.len() {
                return Err(Error::from(ClearSigningError::OutOfBounds))?;
            }
            let slot = &calldata[offset..offset + 32];
            let param = match t {
                AtomicType::Address => {
                    check_padding_zero(slot, 20)?;
                    ParsedParameter::Address(slot[12..].to_vec())
                }
                AtomicType::Bool => {
                    check_padding_zero(slot, 1)?;
                    ParsedParameter::Bool(slot[31] != 0)
                }
                _ => {
                    // All uintN — parse as U256
                    ParsedParameter::Uint(U256::from_big_endian(slot))
                }
            };
            Ok((param, 32))
        }
        AbiValue::Dynamic(_) => {
            // pointer + length + data
            if offset + 32 > calldata.len() {
                return Err(Error::from(ClearSigningError::OutOfBounds))?;
            }
            let ptr = U256::from_big_endian(&calldata[offset..offset + 32]).as_usize();
            if ptr + 32 > calldata.len() {
                return Err(Error::from(ClearSigningError::OutOfBounds))?;
            }
            let len = U256::from_big_endian(&calldata[ptr..ptr + 32]).as_usize();
            if ptr + 32 + len > calldata.len() {
                return Err(Error::from(ClearSigningError::OutOfBounds))?;
            }
            Ok((
                ParsedParameter::Bytes(calldata[ptr + 32..ptr + 32 + len].to_vec()),
                32,
            ))
        }
        AbiValue::Tuple { fields, .. } => {
            let mut parsed = Vec::new();
            let mut consumed = 0;
            for field in fields {
                let leaf_abi = match field {
                    LeafParser::Atomic(t) => AbiValue::Atomic(*t),
                    LeafParser::Dynamic(t) => AbiValue::Dynamic(*t),
                };
                let (val, c) = parse_abi_value(&leaf_abi, calldata, offset + consumed)?;
                parsed.push(val);
                consumed += c;
            }
            Ok((ParsedParameter::Tuple(parsed), consumed))
        }
        AbiValue::Array(_) => {
            // dynamic array: pointer → length → elements
            Err(Error::from(ClearSigningError::NotImplemented))?
        }
    }
}

pub(crate) fn _request_definitions(
    chain_id: u64,
    token_address: &[u8],
    func_sig: Option<&[u8]>,
) -> Result<(Option<definitions::Definitions>, Option<DisplayFormat>)> {
    let req = DefinitionRequest {
        chain_id,
        token_address: token_address.to_vec(),
        func_sig: func_sig.map(|sig| sig.to_vec()),
    };

    let resp: DefinitionAck = wire_request(&req, MessageType::DefinitionRequest)?;

    if let Some(definitions) = resp.definitions {
        let defs = definitions::Definitions::from_encoded(
            definitions.encoded_network.as_deref(),
            definitions.encoded_token.as_deref(),
            Some(chain_id),
            None,
        )?;

        let display_format =
            if let Some(encoded_display_format) = definitions.encoded_display_format {
                Some(DisplayFormat::from_encoded(&encoded_display_format)?)
            } else {
                None
            };

        Ok((Some(defs), display_format))
    } else {
        Ok((None, None))
    }
}

// TODO: implement
pub(crate) fn try_confirm<'a>(
    data: &[u8],
    address_bytes: &[u8],
    // _msg: &SignTx,
    dp: &'a Bip32Path,
    value: U256,
    to: &'a str,
    chunkify: bool,
    chain_id: u64,
    _definitions: Option<&ethereum::Definitions>,
    defs: &definitions::Definitions,
    maximum_fee: &str,
    fee_items: &[Property<'a>],
    payment_request_verifier: Option<&'a mut PaymentRequestVerifier>,
    payment_req: Option<&'a PaymentRequest>,
    supports_definition_request: Option<bool>,
) -> Result<bool> {
    if address_bytes.is_empty() {
        return Ok(false);
    }

    if data.len() < SC_FUNC_SIG_BYTES {
        return Ok(false);
    }

    let (func_sig, calldata) = data.split_at(SC_FUNC_SIG_BYTES);

    let mut display_format = None;
    for f in get_all_display_formats() {
        // Start by trying built-in definitions...
        if f.func_sig == func_sig && f.matches_context(chain_id, address_bytes) {
            display_format = Some(f);
            break;
        }
    }
    if display_format.is_none() {
        // ... finally request the display format via another call!

        if supports_definition_request.is_some() {
            let (_, f) = _request_definitions(chain_id, address_bytes, Some(func_sig))?;
            if let Some(f) = f
                && f.func_sig == func_sig
                && f.matches_context(chain_id, address_bytes)
            {
                display_format = Some(f);
            }
        }
    }

    if let Some(display_format) = display_format {
        if payment_request_verifier.is_some()
            && display_format.func_sig != get_transfer_display_format().func_sig
        {
            return Err(Error::DataError(
                "Payment Requests only supported for ERC-20 transfers.",
            ));
        }

        // custom treatment of certain functions (APPROVE, TRANSFER)
        if display_format.func_sig == get_approve_display_format().func_sig {
            _handle_approve(
                dp,
                value,
                calldata,
                display_format,
                address_bytes,
                defs,
                maximum_fee,
                fee_items,
                chain_id,
                chunkify,
            )?;
        } else if display_format.func_sig == get_transfer_display_format().func_sig {
            _handle_transfer(
                dp,
                chunkify,
                chain_id,
                calldata,
                &display_format,
                address_bytes,
                defs,
                maximum_fee,
                fee_items,
                payment_request_verifier,
                payment_req,
            )?;
        } else {
            // generic UI for any function that has a `DisplayFormat`
            _handle_generic_ui(dp, value, to, calldata, &display_format, defs, maximum_fee)?;
        }
        Ok(true)
    } else {
        Ok(false)
    }
}

fn _handle_approve<'a>(
    dp: &'a Bip32Path,
    value: U256,
    calldata: &'a [u8],
    display_format: DisplayFormat,
    address_bytes: &'a [u8],
    defs: &'a definitions::Definitions,
    maximum_fee: &str,
    fee_items: &[Property<'a>],
    chain_id: u64,
    chunkify: bool,
) -> Result<()> {
    let from_str = dp.format_path();
    let container = ContainerValues {
        from: Some(from_str.as_str()),
        value,
        to: address_bytes,
    };

    let (args, fields) = display_format.parse_calldata(calldata, &container, defs)?;

    if args.len() != 2 || fields.len() != 2 {
        return Err(Error::from(ClearSigningError::InvalidFormatDefinition));
    }

    // arg0 must be an address (spender)
    let spender_bytes = match &args[0] {
        ParsedParameter::Address(addr) => addr.as_slice(),
        _ => return Err(Error::from(ClearSigningError::InvalidFormatDefinition)),
    };

    if &fields[0].label != "Spender" {
        return Err(Error::from(ClearSigningError::InvalidFormatDefinition));
    }

    // arg1 must be an amount
    let amount = match &args[1] {
        ParsedParameter::Uint(value) => *value,
        _ => return Err(Error::from(ClearSigningError::InvalidFormatDefinition)),
    };

    if fields[1].label != "Amount" {
        return Err(Error::from(ClearSigningError::InvalidFormatDefinition));
    }

    let _token = fields[1].token.as_deref();

    let actual_token = None; // TODO: implent
    let default_token = defs.get_token(address_bytes);

    let mut recipient_str = get_approve_known_address(spender_bytes);
    if recipient_str.is_none() {
        let vault = lookup_vault(defs.network(), spender_bytes);
        if vault != unknown_vault() {
            recipient_str = Some(vault.name);
        }
    }

    let is_revoke = amount == SC_FUNC_APPROVE_REVOKE_AMOUNT;

    require_confirm_approve(
        "",   // TODO
        None, // TODO
        recipient_str.as_deref(),
        dp,
        maximum_fee,
        fee_items,
        chain_id,
        defs.network(),
        actual_token.unwrap_or(&default_token), // TODO: actual
        address_bytes,
        is_revoke,
        chunkify,
    )?;
    Ok(())
}

// TODO: implement
fn _handle_transfer<'a>(
    dp: &'a Bip32Path,
    chunkify: bool,
    chain_id: u64,
    calldata: &'a [u8],
    display_format: &'a DisplayFormat,
    address_bytes: &'a [u8],
    defs: &'a definitions::Definitions,
    maximum_fee: &'a str,
    fee_items: &'a [Property<'a>],
    payment_request_verifier: Option<&'a mut PaymentRequestVerifier>,
    payment_req: Option<&'a PaymentRequest>,
) -> Result<()> {
    let container = ContainerValues {
        from: Some(""),
        value: U256::zero(),
        to: address_bytes,
    };
    let (args, fields) = display_format.parse_calldata(calldata, &container, defs)?;

    if args.len() != 2 || fields.len() != 2 {
        return Err(Error::from(ClearSigningError::InvalidFormatDefinition));
    }

    // let (field0_name, recipient_addr, _), _, _ = fields[0];
    // if field0_name != "To" {
    //     return Err(Error::from(ClearSigningError::InvalidFormatDefinition))?;
    // }
    let recipient_addr = "".to_string(); // TODO: implement

    // assert isinstance(recipient_addr, str)

    // let arg1_raw_value = args[1];
    // let (field1_name, value, _), actual_token, _ = fields[1];
    // if field1_name != "Amount" {
    // return Err(Error::from(ClearSigningError::InvalidFormatDefinition))?;
    // }
    let amount = U256::zero(); // TODO: implement
    let actual_token = None; // TODO: implement
    let default_token = defs.get_token(address_bytes);

    // assert isinstance(arg1_raw_value, int)
    // assert isinstance(value, str)

    if let Some(payment_request_verifier) = payment_request_verifier {
        // SLIP-24 payment requests for ERC-20 token transfers

        let payment_req = payment_req.ok_or(Error::DataError("Missing payment request"))?;

        payment_request_verifier.add_output(amount, &recipient_addr, None)?;
        payment_request_verifier.verify()?;
        require_confirm_payment_request(
            &recipient_addr,
            payment_req,
            dp,
            maximum_fee,
            fee_items,
            chain_id,
            defs.network(),
            Some(actual_token.unwrap_or(&default_token)),
            None, // &address_from_bytes(address_bytes, Some(defs.network())),
        )?;
    } else {
        require_confirm_tx(
            Some(&recipient_addr),
            "", // TODO
            address_bytes,
            dp,
            maximum_fee,
            fee_items,
            None, //actual_token || defs.get_token(address_bytes),
            true,
            chunkify,
        )?;
    }
    Ok(())
}

// TODO: implement
fn _handle_generic_ui<'a>(
    _dp: &'a Bip32Path,
    _value: U256,
    to: &'a str,
    _calldata: &'a [u8],
    display_format: &'a DisplayFormat,
    _defs: &'a definitions::Definitions,
    maximum_fee: &'a str,
) -> Result<()> {
    let properties_to_confirm = vec![];

    // let containter = ContainerValues {
    //     from: Some(&dp.format_path()),
    //     value,
    //     to: &[], // TODO
    // };
    // let (_, fields) = display_format.parse_calldata(calldata, &containter, defs)?;

    // for (label, formatted, hint), actual_token, actual_token_address in fields:
    //     if isinstance(formatted, AboveThreshold):
    //         formatted = formatted.message
    //     properties_to_confirm.append((label, formatted, hint))
    //     if actual_token is tokens.UNKNOWN_TOKEN:
    //         assert actual_token_address is not None
    //         token_address_str = address_from_bytes(actual_token_address, defs.network)
    //         token_address_property: StrPropertyType = (
    //             TR.ethereum__token_contract,
    //             token_address_str,
    //             None,
    //         )
    //         properties_to_confirm.append(token_address_property)

    let recipient_str = get_approve_known_address(&bytes_from_address(to)?)
        .ok_or(Error::DataError("Address is not known"))?;

    require_confirm_clear_signing(
        &recipient_str,
        &display_format.intent,
        &properties_to_confirm,
        maximum_fee,
    )?;
    Ok(())
}

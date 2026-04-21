use crate::{
    definitions::unknown_network,
    proto::definitions::{NetworkInfo, TokenInfo},
    proto::ethereum::typed_data_struct_ack::{DataType, FieldType},
    strutil::{hex_decode, hex_encode},
    uformat,
};
#[cfg(not(test))]
use alloc::{
    string::{String, ToString},
    vec,
    vec::Vec,
};
use primitive_types::U256;
#[cfg(test)]
use std::{
    string::{String, ToString},
    vec,
    vec::Vec,
};
use trezor_app_sdk::{Error, Result, crypto::keccak_256, info};

const RSKIP60_NETWORKS: [u64; 2] = [30, 31];

/// Converts address in bytes to a checksummed string as defined
/// in https://github.com/ethereum/EIPs/blob/master/EIPS/eip-55.md
pub fn address_from_bytes(address_bytes: &[u8], network: Option<&NetworkInfo>) -> String {
    let default = unknown_network();
    let network_info = network.unwrap_or(&default);
    let prefix = if RSKIP60_NETWORKS.contains(&network_info.chain_id) {
        uformat!("{}0x", network_info.chain_id)
    } else {
        String::new()
    };

    let address_hex = hex_encode(address_bytes);

    // Calculate sha3-256 keccak hash
    let hash_input = uformat!("{}{}", prefix.as_str(), address_hex.as_str());

    let digest = keccak_256(hash_input.as_bytes());

    let mut result = String::from("0x");

    for (i, ch) in address_hex.chars().enumerate() {
        let digest_byte = digest[i / 2];
        let bit = if i % 2 == 0 {
            0x80 // even letter -> high nibble
        } else {
            0x08 // odd letter -> low nibble
        };

        if digest_byte & bit != 0 {
            result.push(ch.to_ascii_uppercase());
        } else {
            result.push(ch);
        }
    }

    result
}

pub fn bytes_from_address(address: &str) -> Result<Vec<u8>> {
    if address.len() == 40 {
        hex_decode(address).map_err(|_| Error::DataError("Invalid address format"))
    } else if address.len() == 42 {
        if !address.starts_with("0x") && !address.starts_with("0X") {
            Err(Error::DataError("invalid beginning of an address"))
        } else {
            hex_decode(&address[2..]).map_err(|_| Error::DataError("Invalid address format"))
        }
    } else if address.is_empty() {
        Ok(vec![])
    } else {
        Err(Error::DataError("Invalid address length"))
    }
}

/// Create a string from type definition (like uint256 or bytes16).
pub fn get_type_name(field: &FieldType) -> Result<String> {
    let data_type = field.data_type;
    let size = field.size;

    if data_type == DataType::Struct as i32 {
        return Ok(field
            .struct_name
            .clone()
            .ok_or(Error::DataError("Missing struct name"))?);
    } else if data_type == DataType::Array as i32 {
        let entry_type = field
            .entry_type
            .as_ref()
            .expect("validate_field_type must ensure entry_type for array");
        let inner = get_type_name(entry_type.as_ref())?;
        return match size {
            Some(n) => Ok(uformat!("{}[{}]", inner.as_str(), n)),
            None => Ok(uformat!("{}[]", inner.as_str())),
        };
    } else if data_type == DataType::Uint as i32 {
        let n = size.expect("validate_field_type must ensure size for uint");
        return Ok(uformat!("uint{}", n * 8));
    } else if data_type == DataType::Int as i32 {
        let n = size.expect("validate_field_type must ensure size for int");
        return Ok(uformat!("int{}", n * 8));
    } else if data_type == DataType::Bytes as i32 {
        return match size {
            Some(n) if n != 0 => Ok(uformat!("bytes{}", n)),
            _ => Ok("bytes".to_string()),
        };
    } else if data_type == DataType::String as i32 {
        return Ok("string".to_string());
    } else if data_type == DataType::Bool as i32 {
        return Ok("bool".to_string());
    } else if data_type == DataType::Address as i32 {
        return Ok("address".to_string());
    }

    panic!("Unsupported DataType: {}", data_type);
}

/// Used by sign_typed_data module to show data to user.
pub fn decode_typed_data(data: &[u8], type_name: &str) -> Result<String> {
    if type_name.starts_with("bytes") {
        return Ok(hex_encode(data));
    } else if type_name == "string" {
        return core::str::from_utf8(data)
            .map(|s| s.to_string())
            .map_err(|_| Error::DataError("Invalid UTF-8 string"));
    } else if type_name == "address" {
        return Ok(address_from_bytes(data, None));
    } else if type_name == "bool" {
        return Ok(if data == [0x01] { "true" } else { "false" }.to_string());
    } else if type_name.starts_with("uint") {
        if data.len() > 32 {
            return Err(Error::DataError("Invalid uint length"));
        }
        // TODO: better implement parsing int value from bytes
        let v = U256::from_big_endian(data);
        return Ok(v.to_string());
    } else if type_name.starts_with("int") {
        if data.len() > 16 {
            return Err(Error::DataError("Invalid int length"));
        }
        let mut buf = [0u8; 16];
        buf[16 - data.len()..].copy_from_slice(data);
        let s = i128::from_be_bytes(buf);
        return Ok(s.to_string());
    }

    Err(Error::ValueError(
        "Unsupported data type for direct field decoding",
    ))
}

pub fn get_fee_items_regular(
    gas_price: U256,
    gas_limit: U256,
    network: &NetworkInfo,
) -> [(String, String, bool); 2] {
    let gas_limit_str = uformat!("{} units", gas_limit.to_string().as_str());
    let gas_price_str = format_ethereum_amount(gas_price, None, network, true);

    [
        (tr!("ethereum__gas_limit").into(), gas_limit_str, false),
        (tr!("ethereum__gas_price").into(), gas_price_str, false),
    ]
}

pub fn get_fee_items_eip1559(
    max_gas_fee: U256,
    max_priority_fee: U256,
    gas_limit: U256,
    network: &NetworkInfo,
) -> [(String, String, bool); 3] {
    let gas_limit_str = uformat!("{} units", gas_limit.to_string().as_str());
    let max_gas_fee_str = format_ethereum_amount(max_gas_fee, None, network, true);
    let max_priority_fee_str = format_ethereum_amount(max_priority_fee, None, network, true);
    [
        (tr!("ethereum__gas_limit").into(), gas_limit_str, false),
        (
            tr!("ethereum__max_gas_price").into(),
            max_gas_fee_str,
            false,
        ),
        (
            tr!("ethereum__priority_fee").into(),
            max_priority_fee_str,
            false,
        ),
    ]
}

pub fn format_ethereum_amount(
    value: U256,
    token: Option<&TokenInfo>,
    network: &NetworkInfo,
    force_unit_gwei: bool,
) -> String {
    let (mut suffix, mut decimals) = if let Some(token) = token {
        (token.symbol.as_str().to_string(), token.decimals as usize)
    } else {
        (network.symbol.as_str().to_string(), 18usize)
    };

    let digits = value.to_string();

    if force_unit_gwei {
        debug_assert!(token.is_none());
        debug_assert!(decimals >= 9);
        decimals -= 9;
        suffix = "Gwei".to_string();
    } else if decimals > 9 {
        if digits.len() <= (decimals - 9) {
            suffix = uformat!("Wei {}", suffix.as_str());
            decimals = 0;
        }
    }

    let amount = format_amount_from_digits(&digits, decimals);
    uformat!("{} {}", amount.as_str(), suffix.as_str())
}

fn format_amount_from_digits(digits: &str, decimals: usize) -> String {
    let mut out = String::with_capacity(digits.len() + digits.len() / 3 + 3);

    if decimals == 0 {
        push_grouped_digits(&mut out, digits);
        return out;
    }

    if digits.len() <= decimals {
        out.push('0');
        out.push('.');
        for _ in 0..(decimals - digits.len()) {
            out.push('0');
        }
        out.push_str(digits);
    } else {
        let split = digits.len() - decimals;
        let (int_part, frac_part) = digits.split_at(split);
        push_grouped_digits(&mut out, int_part);
        out.push('.');
        out.push_str(frac_part);
    }

    while out.ends_with('0') {
        out.pop();
    }
    if out.ends_with('.') {
        out.pop();
    }

    out
}

fn push_grouped_digits(out: &mut String, digits: &str) {
    for (i, ch) in digits.chars().enumerate() {
        if i != 0 && (digits.len() - i) % 3 == 0 {
            out.push(',');
        }
        out.push(ch);
    }
}

pub fn write_compact_size(n: u32) -> Vec<u8> {
    let mut out = Vec::with_capacity(5);

    if n < 253 {
        out.push(n as u8);
    } else if n < 0x1_0000 {
        out.push(253);
        out.extend_from_slice(&(n as u16).to_le_bytes());
    } else {
        out.push(254);
        out.extend_from_slice(&(n as u32).to_le_bytes());
    }

    out
}

#[derive(Debug, Clone)]
pub struct Refund {
    pub address: String,
    pub account: Option<String>,
    pub account_path: Option<String>,
}

impl Refund {
    pub fn new(address: &str, account: Option<&str>, account_path: Option<&str>) -> Result<Self> {
        Ok(Self {
            address: address.to_string(),
            account: account.map(|s| s.to_string()),
            account_path: account_path.map(|s| s.to_string()),
        })
    }
}

#[derive(Debug, Clone)]
pub struct Trade {
    pub sell_amount: Option<String>,
    pub buy_amount: String,
    pub address: String,
    pub account: Option<String>,
    pub account_path: Option<String>,
}

impl Trade {
    pub fn new(
        sell_amount: Option<&str>,
        buy_amount: &str,
        address: &str,
        account: Option<&str>,
        account_path: Option<&str>,
    ) -> Result<Self> {
        if let Some(ref sell_amount) = sell_amount {
            if !sell_amount.starts_with('-') {
                return Err(Error::DataError("Invalid sell amount format"));
            }
        }

        if !buy_amount.starts_with('+') {
            return Err(Error::DataError("Invalid buy amount format"));
        }

        Ok(Self {
            sell_amount: sell_amount.map(|s| s.to_string()),
            buy_amount: buy_amount.to_string(),
            address: address.to_string(),
            account: account.map(|s| s.to_string()),
            account_path: account_path.map(|s| s.to_string()),
        })
    }
}

pub fn is_swap(trades: &[Trade]) -> Result<bool> {
    let has_sell_amount = trades.iter().any(|t| t.sell_amount.is_some());
    let has_missing_sell_amount = trades.iter().any(|t| t.sell_amount.is_none());

    if has_sell_amount && has_missing_sell_amount {
        return Err(Error::DataError("Inconsistent trade data"));
    }

    Ok(has_sell_amount)
}

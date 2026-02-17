extern crate alloc;

use crate::definitions::unknown_network;
use crate::proto::definitions::{EthereumNetworkInfo, EthereumTokenInfo};
use crate::proto::ethereum_eip712::ethereum_typed_data_struct_ack::EthereumDataType;
use crate::strutil::{hex_decode, hex_encode};
use crate::uformat;
use alloc::string::{String, ToString};
use alloc::vec;
use alloc::vec::Vec;
use trezor_app_sdk::Error;
use trezor_app_sdk::crypto::keccak_256;

use trezor_app_sdk::Result;

const RSKIP60_NETWORKS: [u64; 2] = [30, 31];

pub struct Property {
    pub name: Option<String>,
    pub value: Option<String>,
    pub is_mono: Option<bool>,
}

/// Converts address in bytes to a checksummed string as defined
/// in https://github.com/ethereum/EIPs/blob/master/EIPS/eip-55.md
pub fn address_from_bytes(address_bytes: &[u8], chain_id: Option<u64>) -> String {
    let chain_id = chain_id.unwrap_or(unknown_network().chain_id);

    let prefix = if RSKIP60_NETWORKS.contains(&chain_id) {
        let mut s = String::new();
        s.push_str(&chain_id.to_string());
        s.push_str("0x");
        s
    } else {
        String::new()
    };

    let address_hex = hex_encode(address_bytes);

    // Calculate sha3-256 keccak hash
    let mut hash_input = String::new();
    hash_input.push_str(&prefix);
    hash_input.push_str(&address_hex);

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
        hex_decode(address).map_err(|_| Error::DataError)
    } else if address.len() == 42 {
        if !address.starts_with("0x") && !address.starts_with("0X") {
            // TODO Ethereum: invalid beginning of an address
            Err(Error::DataError)
        } else {
            hex_decode(&address[2..]).map_err(|_| Error::DataError)
        }
    } else if address.is_empty() {
        Ok(vec![])
    } else {
        // TODO Ethereum: Invalid address length
        Err(Error::DataError)
    }
}

/// Create a string from type definition (like uint256 or bytes16).
pub fn get_type_name(field: EthereumDataType) -> String {
    // TODO implement
    String::new()
}

/// Used by sign_typed_data module to show data to user.
pub fn decode_typed_data(data: &[u8], type_name: &str) -> Result<String> {
    if type_name.starts_with("bytes") {
        return Ok(hex_encode(data));
    } else if type_name == "string" {
        return core::str::from_utf8(data)
            .map(|s| s.to_string())
            .map_err(|_| Error::InvalidMessage);
    } else if type_name == "address" {
        return Ok(address_from_bytes(data, None));
    } else if type_name == "bool" {
        return Ok(if data == [0x01] { "true" } else { "false" }.to_string());
    } else if type_name.starts_with("uint") {
        let v = u128::from_be_bytes(data.try_into().map_err(|_| Error::InvalidMessage)?);
        return Ok(v.to_string());
    } else if type_name.starts_with("int") {
        let s = i128::from_be_bytes(data.try_into().map_err(|_| Error::InvalidMessage)?);
        return Ok(s.to_string());
    }

    // TODO: ValueError  # Unsupported data type for direct field decoding
    Err(Error::InvalidMessage)
}

pub fn get_fee_items_regular(
    gas_price: u32,
    gas_limit: u32,
    network: &EthereumNetworkInfo,
) -> Vec<Property> {
    let gas_limit_str = uformat!("{} units", gas_limit);
    let gas_price_str = format_ethereum_amount(gas_price, None, network, Some(true));

    vec![
        Property {
            name: Some("Gas Limit".into()),
            value: Some(gas_limit_str),
            is_mono: Some(false),
        },
        Property {
            name: Some("Gas Price".into()),
            value: Some(gas_price_str),
            is_mono: Some(false),
        },
    ]
}

pub fn format_ethereum_amount(
    format: u32,
    token: Option<&EthereumTokenInfo>,
    network: &EthereumNetworkInfo,
    force_unit_gwei: Option<bool>,
) -> String {
    // TODO implement
    String::new()
}

use crate::{
    definitions::unknown_network,
    proto::definitions::{EthereumNetworkInfo, EthereumTokenInfo},
    proto::ethereum_eip712::ethereum_typed_data_struct_ack::EthereumDataType,
    strutil::{hex_decode, hex_encode},
    uformat,
};
#[cfg(not(test))]
use alloc::{
    string::{String, ToString},
    vec,
    vec::Vec,
};
#[cfg(test)]
use std::{
    string::{String, ToString},
    vec,
    vec::Vec,
};
use trezor_app_sdk::{Error, Result, crypto::keccak_256};

const RSKIP60_NETWORKS: [u64; 2] = [30, 31];

pub struct Property {
    pub name: Option<String>,
    pub value: Option<String>,
    pub is_mono: Option<bool>,
}

/// Converts address in bytes to a checksummed string as defined
/// in https://github.com/ethereum/EIPs/blob/master/EIPS/eip-55.md
pub fn address_from_bytes(address_bytes: &[u8], network: Option<&EthereumNetworkInfo>) -> String {
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
pub fn get_type_name(_field: EthereumDataType) -> String {
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
        if data.len() > 16 {
            return Err(Error::InvalidMessage);
        }
        let mut buf = [0u8; 16];
        buf[16 - data.len()..].copy_from_slice(data);
        let v = u128::from_be_bytes(buf);
        return Ok(v.to_string());
    } else if type_name.starts_with("int") {
        if data.len() > 16 {
            return Err(Error::InvalidMessage);
        }
        let mut buf = [0u8; 16];
        buf[16 - data.len()..].copy_from_slice(data);
        let s = i128::from_be_bytes(buf);
        return Ok(s.to_string());
    }

    // TODO: ValueError  # Unsupported data type for direct field decoding
    Err(Error::InvalidMessage)
}

pub fn get_fee_items_regular(
    gas_price: u128,
    gas_limit: u128,
    network: &EthereumNetworkInfo,
) -> Vec<Property> {
    let gas_limit_str = uformat!("{} units", gas_limit);
    let gas_price_str = format_ethereum_amount(gas_price, None, network, true);

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
    _value: u128,
    _token: Option<&EthereumTokenInfo>,
    _network: &EthereumNetworkInfo,
    _force_unit_gwei: bool,
) -> String {
    // TODO implement
    String::new()
}

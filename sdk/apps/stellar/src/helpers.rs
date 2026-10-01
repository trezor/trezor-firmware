use crate::{
    alloc_types::{String, Vec},
    consts::ENVELOPE_TYPE_CONTRACT_ID,
    proto::stellar::Asset,
    writers::{
        write_contract_id_preimage_from_address, write_contract_id_preimage_from_asset,
        write_hash_id_preimage_header,
    },
};
use trezor_app_sdk::{
    Error, Result, ResultExt,
    crypto::{self, HasherExt as _, HashingAlgorithm},
};

// Stellar strkey version bytes
// See: https://github.com/stellar/stellar-protocol/blob/master/ecosystem/sep-0023.md
pub const STRKEY_ED25519_PUBLIC_KEY: u8 = 6; // G...
pub const STRKEY_CONTRACT: u8 = 2; // C...
pub const STRKEY_MUXED_ACCOUNT: u8 = 12; // M...
pub const STRKEY_CLAIMABLE_BALANCE: u8 = 1; // B...
pub const STRKEY_LIQUIDITY_POOL: u8 = 11; // L...

fn payload_size(version: u8) -> Option<usize> {
    match version {
        STRKEY_ED25519_PUBLIC_KEY => Some(32),
        STRKEY_CONTRACT => Some(32),
        STRKEY_MUXED_ACCOUNT => Some(40),
        STRKEY_CLAIMABLE_BALANCE => Some(33),
        STRKEY_LIQUIDITY_POOL => Some(32),
        _ => None,
    }
}

const BASE32_ALPHABET: &[u8; 32] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";

/// RFC 4648 base32 without padding.
fn base32_encode(data: &[u8]) -> String {
    let mut out = String::with_capacity((data.len() * 8).div_ceil(5));
    let mut buffer: u32 = 0;
    let mut bits = 0;
    for &byte in data {
        buffer = (buffer << 8) | byte as u32;
        bits += 8;
        while bits >= 5 {
            bits -= 5;
            out.push(BASE32_ALPHABET[((buffer >> bits) & 0x1f) as usize] as char);
        }
        buffer &= (1 << bits) - 1;
    }
    if bits > 0 {
        out.push(BASE32_ALPHABET[((buffer << (5 - bits)) & 0x1f) as usize] as char);
    }
    out
}

/// RFC 4648 base32 without padding. Trailing unused bits are not checked
/// here; callers get canonicality by re-encoding (see [`decode_strkey`]).
fn base32_decode(s: &str) -> Result<Vec<u8>> {
    let mut out = Vec::with_capacity(s.len() * 5 / 8);
    let mut buffer: u32 = 0;
    let mut bits = 0;
    for c in s.bytes() {
        let value = match c {
            b'A'..=b'Z' => c - b'A',
            b'2'..=b'7' => c - b'2' + 26,
            _ => return Err(Error::DataError("Strkey not base32-encoded")),
        };
        buffer = (buffer << 5) | value as u32;
        bits += 5;
        if bits >= 8 {
            bits -= 8;
            out.push((buffer >> bits) as u8);
            buffer &= (1 << bits) - 1;
        }
    }
    Ok(out)
}

/// CRC-16/XMODEM (initial value 0x0000, as Stellar configures it), returned
/// little-endian.
fn crc16_checksum(data: &[u8]) -> [u8; 2] {
    let mut crc: u16 = 0;
    for &byte in data {
        crc ^= (byte as u16) << 8;
        for _ in 0..8 {
            crc = if crc & 0x8000 != 0 {
                (crc << 1) ^ 0x1021
            } else {
                crc << 1
            };
        }
    }
    crc.to_le_bytes()
}

/// Encodes data to the Stellar strkey format.
pub fn encode_strkey(version: u8, data: &[u8]) -> String {
    let mut payload = Vec::with_capacity(1 + data.len() + 2);
    payload.push(version << 3);
    payload.extend_from_slice(data);
    let checksum = crc16_checksum(&payload);
    payload.extend_from_slice(&checksum);
    base32_encode(&payload)
}

/// Decodes and validates a Stellar strkey into `(version, data)`.
///
/// Follows SEP-0023. Besides the CRC-16 checksum, canonicality is enforced by
/// re-encoding: any input with an invalid length, non-zero unused bits or an
/// unsupported algorithm re-encodes differently and is rejected.
pub fn decode_strkey(strkey: &str) -> Result<(u8, Vec<u8>)> {
    let bytes = base32_decode(strkey)?;
    if bytes.len() < 3 {
        return Err(Error::DataError("Invalid strkey checksum"));
    }
    let (body, checksum) = bytes.split_at(bytes.len() - 2);
    if crc16_checksum(body) != checksum {
        return Err(Error::DataError("Invalid strkey checksum"));
    }
    let version = body[0] >> 3;
    let data = &body[1..];
    if encode_strkey(version, data) != strkey {
        return Err(Error::DataError("Invalid strkey encoding"));
    }
    let Some(expected_len) = payload_size(version) else {
        return Err(Error::DataError("Unsupported strkey version"));
    };
    if data.len() != expected_len {
        return Err(Error::DataError("Invalid strkey payload length"));
    }
    if version == STRKEY_CLAIMABLE_BALANCE && data[0] != 0 {
        // only CLAIMABLE_BALANCE_ID_TYPE_V0 exists
        return Err(Error::DataError("Invalid claimable balance type"));
    }
    Ok((version, data.to_vec()))
}

/// Extracts the public key from an account address (G...).
pub fn public_key_from_address(address: &str) -> Result<[u8; 32]> {
    let (version, data) = decode_strkey(address)?;
    if version != STRKEY_ED25519_PUBLIC_KEY {
        return Err(Error::DataError("Expected a public key address"));
    }
    data.try_into()
        .map_err(|_| Error::DataError("Invalid strkey payload length"))
}

/// Returns the base32-encoded version of public key bytes (G...).
pub fn address_from_public_key(pubkey: &[u8]) -> String {
    encode_strkey(STRKEY_ED25519_PUBLIC_KEY, pubkey)
}

pub fn sha256(data: &[u8]) -> [u8; 32] {
    let mut hasher = crypto::get_hasher(HashingAlgorithm::Sha256);
    hasher.update(data);
    let mut digest = [0u8; 32];
    digest.copy_from_slice(hasher.finalize().as_slice());
    digest
}

/// Derives the address (C...) of the contract an address deploys with a salt.
pub fn contract_address_from_address(
    network_id: &[u8; 32],
    address: &str,
    salt: &[u8],
) -> Result<String> {
    let mut w = Vec::new();
    write_hash_id_preimage_header(&mut w, ENVELOPE_TYPE_CONTRACT_ID, network_id);
    write_contract_id_preimage_from_address(&mut w, address, salt).c()?;
    Ok(encode_strkey(STRKEY_CONTRACT, &sha256(&w)))
}

/// Derives the address (C...) of an asset's Stellar Asset Contract (SAC).
pub fn contract_address_from_asset(network_id: &[u8; 32], asset: &Asset) -> Result<String> {
    let mut w = Vec::new();
    write_hash_id_preimage_header(&mut w, ENVELOPE_TYPE_CONTRACT_ID, network_id);
    write_contract_id_preimage_from_asset(&mut w, asset).c()?;
    Ok(encode_strkey(STRKEY_CONTRACT, &sha256(&w)))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn strkey_roundtrip() {
        let pubkey = [0x42u8; 32];
        let address = address_from_public_key(&pubkey);
        assert_eq!(address.len(), 56);
        assert!(address.starts_with('G'));
        assert_eq!(public_key_from_address(&address).unwrap(), pubkey);
    }

    #[test]
    fn strkey_rejects_bad_checksum() {
        let mut address = address_from_public_key(&[0x42u8; 32]);
        let last = address.pop().unwrap();
        address.push(if last == 'A' { 'B' } else { 'A' });
        assert!(decode_strkey(&address).is_err());
    }

    #[test]
    fn crc16_known_vector() {
        // CRC-16/XMODEM of "123456789" is 0x31C3.
        assert_eq!(crc16_checksum(b"123456789"), 0x31c3u16.to_le_bytes());
    }
}

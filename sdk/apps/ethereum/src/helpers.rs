use crate::{
    alloc_types::{Box, String, ToString, Vec, vec},
    definitions::unknown_network,
    layout::{confirm_blob_intro, confirm_blob_prefix},
    proto::definitions::{NetworkInfo, TokenInfo},
    proto::{
        common::button_request::ButtonRequestType,
        ethereum::typed_data_struct_ack::{DataType, FieldType},
    },
    strutil::{hex_decode, hex_encode},
    uformat,
};
use primitive_types::U256;
use trezor_app_sdk::{Error, Result, ResultExt, crypto, ui};

const RSKIP60_NETWORKS: [u64; 2] = [30, 31];

/// Converts address in bytes to a checksummed string as defined
/// in https://github.com/ethereum/EIPs/blob/master/EIPS/eip-55.md
pub fn address_from_bytes(address_bytes: &[u8], network: Option<&NetworkInfo>) -> Result<String> {
    let default = unknown_network();
    let network_info = network.unwrap_or(&default);
    let prefix = if RSKIP60_NETWORKS.contains(&network_info.chain_id) {
        uformat!("{}0x", network_info.chain_id)
    } else {
        String::new()
    };

    let address_hex =
        hex_encode(address_bytes).map_err(|_| Error::DataError("Failed to hex-encode message"))?;

    // Calculate sha3-256 keccak hash
    let hash_input = uformat!("{}{}", prefix.as_str(), address_hex.as_str());

    let mut hasher = crypto::Keccak256::new(Some(hash_input.as_bytes()));
    let digest = hasher.digest();

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

    Ok(result)
}

pub fn bytes_from_address(address: &str) -> Result<Vec<u8>> {
    if address.len() == 40 {
        Ok(hex_decode(address).map_err(|_| Error::DataError("Invalid address format"))?)
    } else if address.len() == 42 {
        if !address.starts_with("0x") && !address.starts_with("0X") {
            Err(Error::DataError("invalid beginning of an address"))?
        } else {
            Ok(
                hex_decode(&address[2..])
                    .map_err(|_| Error::DataError("Invalid address format"))?,
            )
        }
    } else if address.is_empty() {
        Ok(vec![])
    } else {
        Err(Error::DataError("Invalid address length"))?
    }
}

/// Create a string from type definition (like uint256 or bytes16).
pub fn get_type_name(field: &FieldType) -> Result<String> {
    let data_type = field.data_type;
    let size = field.size;

    if data_type == DataType::Struct as i32 {
        return field
            .struct_name
            .clone()
            .ok_or(Error::DataError("Missing struct name"));
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
        return hex_encode(data).map_err(|_| Error::DataError("Failed to hex-encode data"));
    } else if type_name == "string" {
        return core::str::from_utf8(data)
            .map(|s| s.to_string())
            .map_err(|_| Error::DataError("Invalid UTF-8 string"));
    } else if type_name == "address" {
        return address_from_bytes(data, None).context("Failed to convert bytes to address");
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
) -> Result<[(String, String, bool); 2]> {
    let gas_limit_str = uformat!("{} units", gas_limit.to_string().as_str());
    let gas_price_str = format_ethereum_amount(gas_price, None, network, true)
        .context("Failed to create regular fee items")?;

    Ok([
        (tr!("ethereum__gas_limit").into(), gas_limit_str, false),
        (tr!("ethereum__gas_price").into(), gas_price_str, false),
    ])
}

pub fn get_fee_items_eip1559(
    max_gas_fee: U256,
    max_priority_fee: U256,
    gas_limit: U256,
    network: &NetworkInfo,
) -> Result<[(String, String, bool); 3]> {
    let gas_limit_str = uformat!("{} units", gas_limit.to_string().as_str());
    let max_gas_fee_str = format_ethereum_amount(max_gas_fee, None, network, true)
        .context("Failed to create gas fee string")?;
    let max_priority_fee_str = format_ethereum_amount(max_priority_fee, None, network, true)
        .context("Failed to create priority fee string")?;
    Ok([
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
    ])
}

pub fn format_ethereum_amount(
    value: U256,
    token: Option<&TokenInfo>,
    network: &NetworkInfo,
    force_unit_gwei: bool,
) -> Result<String> {
    let (mut suffix, mut decimals) = if let Some(token) = token {
        (token.symbol.as_str().to_string(), token.decimals as usize)
    } else {
        (network.symbol.as_str().to_string(), 18usize)
    };

    let digits = value.to_string();

    if force_unit_gwei {
        if token.is_some() {
            return Err(Error::DataError("Cannot force Gwei unit for tokens"));
        }
        if decimals < 9 {
            return Err(Error::DataError(
                "Cannot force Gwei unit for networks with decimals < 9",
            ));
        }
        decimals -= 9;
        suffix = "Gwei".to_string();
    } else if decimals > 9 && digits.len() <= (decimals - 9) {
        suffix = uformat!("Wei {}", suffix.as_str());
        decimals = 0;
    }

    let amount = format_amount_from_digits(&digits, decimals);
    Ok(uformat!("{} {}", amount.as_str(), suffix.as_str()))
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
        if i != 0 && (digits.len() - i).is_multiple_of(3) {
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
        out.extend_from_slice(&(n).to_le_bytes());
    }

    out
}

// #[derive(Debug, Clone)]
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

// #[derive(Debug, Clone)]
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
        if let Some(sell_amount) = sell_amount
            && !sell_amount.starts_with('-')
        {
            return Err(Error::DataError("Invalid sell amount format"))?;
        }

        if !buy_amount.starts_with('+') {
            return Err(Error::DataError("Invalid buy amount format"))?;
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

fn progress_value(total_len: usize, progress_len: usize) -> Result<u32> {
    if progress_len > total_len {
        return Err(Error::DataError("Progress length exceeds total length"));
    }
    if total_len == 0 {
        Ok(1000)
    } else {
        Ok((1000 * progress_len as u32) / total_len as u32)
    }
}

pub fn get_progress_indicator<'a>(
    total_len: usize,
    mut progress_len: usize,
) -> Result<Box<dyn FnMut(&[u8]) -> Result<()> + 'a>> {
    let _value = progress_value(total_len, progress_len)?;

    Ok(Box::new(move |chunk: &[u8]| {
        progress_len += chunk.len();

        ui::update_progress(None, progress_value(total_len, progress_len)?)?;
        Ok(())
    }))
}

pub fn get_data_confirmer(total_len: usize) -> Box<dyn FnMut(&[u8]) -> Result<()>> {
    let mut confirmed_len: usize = 0;
    let mut progress_bar: Option<Box<dyn FnMut(&[u8]) -> Result<()>>> = None;
    let mut first = true;

    Box::new(move |chunk: &[u8]| {
        if first {
            first = false;
            let subtitle = uformat!("{} bytes", total_len.to_string().as_str());
            let skip = confirm_blob_intro(
                tr!("ethereum__title_input_data"),
                chunk,
                subtitle.as_str(),
                tr!("buttons__confirm"),
                tr!("send__cancel_sign"),
                "confirm_data",
                ButtonRequestType::SignTx,
            )?;

            if skip {
                let mut pb = get_progress_indicator(total_len, 0)
                    .context("Failed to create progress indicator")?;
                return pb(chunk);
            }
        }

        if let Some(ref mut pb) = progress_bar {
            return pb(chunk);
        }

        let mut remaining = chunk;
        loop {
            debug_assert!(confirmed_len <= total_len);

            let prefix_len = confirm_blob_prefix(
                remaining,
                total_len,
                confirmed_len,
                "confirm_data",
                ButtonRequestType::SignTx,
            )?;

            match prefix_len {
                None => {
                    let mut pb = get_progress_indicator(total_len, confirmed_len)
                        .context("Failed to create progress indicator")?;
                    pb(remaining)?;
                    progress_bar = Some(pb);
                    return Ok(());
                }
                Some(n) => {
                    confirmed_len += n;
                    remaining = &remaining[n..];
                    if remaining.is_empty() {
                        return Ok(());
                    }
                }
            }
        }
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::definitions::{by_chain_id, unknown_network};
    use crate::proto::definitions::{NetworkInfo, TokenInfo};
    use crate::strutil::hex_decode;
    use crate::test_init;
    use crate::tokens::unknown_token;

    fn setup() {
        test_init::init_sdk();
    }

    fn _make_eth_network(
        chain_id: Option<u64>,
        slip44: Option<u32>,
        symbol: Option<&str>,
        name: Option<&str>,
    ) -> NetworkInfo {
        NetworkInfo {
            chain_id: chain_id.unwrap_or(0),
            slip44: slip44.unwrap_or(0),
            symbol: symbol.unwrap_or("FAKE").into(),
            name: name.unwrap_or("Fake network").into(),
        }
    }

    fn _make_eth_token(
        symbol: Option<&str>,
        decimals: Option<u32>,
        address: Option<&[u8]>,
        chain_id: Option<u64>,
        name: Option<&str>,
    ) -> TokenInfo {
        TokenInfo {
            symbol: symbol.unwrap_or("FAKE").into(),
            decimals: decimals.unwrap_or(18),
            address: address.unwrap_or(b"").to_vec(),
            chain_id: chain_id.unwrap_or(0),
            name: name.unwrap_or("Fake token").into(),
        }
    }

    #[test]
    fn test_denominations() {
        let network = by_chain_id(1);

        let text = format_ethereum_amount(1.into(), None, &network, false).unwrap();
        assert_eq!(text, "1 Wei ETH");
        let text = format_ethereum_amount(1000.into(), None, &network, false).unwrap();
        assert_eq!(text, "1,000 Wei ETH");
        let text = format_ethereum_amount(1000000.into(), None, &network, false).unwrap();
        assert_eq!(text, "1,000,000 Wei ETH");
        let text = format_ethereum_amount(10000000.into(), None, &network, false).unwrap();
        assert_eq!(text, "10,000,000 Wei ETH");
        let text = format_ethereum_amount(100000000.into(), None, &network, false).unwrap();
        assert_eq!(text, "100,000,000 Wei ETH");
        let text = format_ethereum_amount(1000000000.into(), None, &network, false).unwrap();
        assert_eq!(text, "0.000000001 ETH");
        let text = format_ethereum_amount(10000000000u128.into(), None, &network, false).unwrap();
        assert_eq!(text, "0.00000001 ETH");
        let text = format_ethereum_amount(100000000000u128.into(), None, &network, false).unwrap();
        assert_eq!(text, "0.0000001 ETH");
        let text = format_ethereum_amount(1000000000000u128.into(), None, &network, false).unwrap();
        assert_eq!(text, "0.000001 ETH");
        let text =
            format_ethereum_amount(10000000000000u128.into(), None, &network, false).unwrap();
        assert_eq!(text, "0.00001 ETH");
        let text =
            format_ethereum_amount(100000000000000u128.into(), None, &network, false).unwrap();
        assert_eq!(text, "0.0001 ETH");
        let text =
            format_ethereum_amount(1000000000000000u128.into(), None, &network, false).unwrap();
        assert_eq!(text, "0.001 ETH");
        let text =
            format_ethereum_amount(10000000000000000u128.into(), None, &network, false).unwrap();
        assert_eq!(text, "0.01 ETH");
        let text =
            format_ethereum_amount(100000000000000000u128.into(), None, &network, false).unwrap();
        assert_eq!(text, "0.1 ETH");
        let text =
            format_ethereum_amount(1000000000000000000u128.into(), None, &network, false).unwrap();
        assert_eq!(text, "1 ETH");
        let text =
            format_ethereum_amount(10000000000000000000u128.into(), None, &network, false).unwrap();
        assert_eq!(text, "10 ETH");
        let text = format_ethereum_amount(100000000000000000000u128.into(), None, &network, false)
            .unwrap();
        assert_eq!(text, "100 ETH");
        let text = format_ethereum_amount(1000000000000000000000u128.into(), None, &network, false)
            .unwrap();
        assert_eq!(text, "1,000 ETH");
    }

    #[test]
    fn test_force_units() {
        let network = by_chain_id(1);
        let wei_amount = U256::from(100_000_000);
        let text = format_ethereum_amount(wei_amount, None, &network, false).unwrap();
        assert_eq!(text, "100,000,000 Wei ETH");
        let text = format_ethereum_amount(wei_amount, None, &network, true).unwrap();
        assert_eq!(text, "0.1 Gwei");
    }

    #[test]
    fn test_precision() {
        let network = by_chain_id(1);
        let text =
            format_ethereum_amount(1000000000000000001u128.into(), None, &network, false).unwrap();
        assert_eq!(text, "1.000000000000000001 ETH");
        let text =
            format_ethereum_amount(10000000000000000001u128.into(), None, &network, false).unwrap();
        assert_eq!(text, "10.000000000000000001 ETH");
    }

    #[test]
    fn test_symbols() {
        let fake_network = _make_eth_network(None, None, Some("FAKE"), None);
        let text = format_ethereum_amount(1.into(), None, &fake_network, false).unwrap();
        assert_eq!(text, "1 Wei FAKE");
        let text =
            format_ethereum_amount(1000000000000000000u128.into(), None, &fake_network, false)
                .unwrap();
        assert_eq!(text, "1 FAKE");
        let text =
            format_ethereum_amount(1000000000000000001u128.into(), None, &fake_network, false)
                .unwrap();
        assert_eq!(text, "1.000000000000000001 FAKE");
    }

    #[test]
    fn test_unknown_chain() {
        let unknown = unknown_network();
        // unknown chain
        let text = format_ethereum_amount(1.into(), None, &unknown, false).unwrap();
        assert_eq!(text, "1 Wei UNKN");
        let text =
            format_ethereum_amount(10000000000000000001u128.into(), None, &unknown, false).unwrap();
        assert_eq!(text, "10.000000000000000001 UNKN");
    }

    #[test]
    fn test_tokens() {
        // tokens with low decimal values
        // USDC has 6 decimals
        let usdc_token = _make_eth_token(Some("USDC"), Some(6), None, None, None);
        let network = by_chain_id(1);

        // when decimals < 10, should never display 'Wei' format
        let text = format_ethereum_amount(1.into(), Some(&usdc_token), &network, false).unwrap();
        assert_eq!(text, "0.000001 USDC");
        let text = format_ethereum_amount(0.into(), Some(&usdc_token), &network, false).unwrap();
        assert_eq!(text, "0 USDC");

        // ICO has 10 decimals
        let ico_token = _make_eth_token(Some("ICO"), Some(10), None, None, None);
        let text = format_ethereum_amount(1.into(), Some(&ico_token), &network, false).unwrap();
        assert_eq!(text, "1 Wei ICO");
        let text = format_ethereum_amount(9.into(), Some(&ico_token), &network, false).unwrap();
        assert_eq!(text, "9 Wei ICO");
        let text = format_ethereum_amount(10.into(), Some(&ico_token), &network, false).unwrap();
        assert_eq!(text, "0.000000001 ICO");
        let text = format_ethereum_amount(11.into(), Some(&ico_token), &network, false).unwrap();
        assert_eq!(text, "0.0000000011 ICO");
    }

    #[test]
    fn test_unknown_token() {
        let unknown_token = unknown_token();
        let unknown_network = unknown_network();
        let text = format_ethereum_amount(1.into(), Some(&unknown_token), &unknown_network, false)
            .unwrap();
        assert_eq!(text, "1 Wei UNKN");
        let text = format_ethereum_amount(0.into(), Some(&unknown_token), &unknown_network, false)
            .unwrap();
        assert_eq!(text, "0 Wei UNKN");
        // unknown token has 0 decimals so is always wei
        let text = format_ethereum_amount(
            1000000000000000000u128.into(),
            Some(&unknown_token),
            &unknown_network,
            false,
        )
        .unwrap();
        assert_eq!(text, "1,000,000,000,000,000,000 Wei UNKN");
    }

    #[test]
    fn test_address_from_bytes_eip55() {
        setup();
        // https://github.com/ethereum/EIPs/blob/master/EIPS/eip-55.md
        let eip55 = [
            "0x52908400098527886E0F7030069857D2E4169EE7",
            "0x8617E340B3D01FA5F11F306F4090FD50E238070D",
            "0xde709f2102306220921060314715629080e2fb77",
            "0x27b1fdb04752bbc536007a920d24acb045561c26",
            "0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed",
            "0xfB6916095ca1df60bB79Ce92cE3Ea74c37c5d359",
            "0xdbF03B407c01E7cD3CBea99509d93f8DDDC8C6FB",
            "0xD1220A0cf47c7B9Be7A2E6BA89F429762e7b9aDb",
        ];
        for s in eip55.iter() {
            let b = hex_decode(&s[2..]).unwrap();
            let h = address_from_bytes(&b, None).unwrap();
            assert_eq!(&h, s);
        }
    }

    #[test]
    fn test_address_from_bytes_rskip60() {
        // https://github.com/rsksmart/RSKIPs/blob/master/IPs/RSKIP60.md
        let rskip60_chain_30 = [
            "0x5aaEB6053f3e94c9b9a09f33669435E7ef1bEAeD",
            "0xFb6916095cA1Df60bb79ce92cE3EA74c37c5d359",
            "0xDBF03B407c01E7CD3cBea99509D93F8Dddc8C6FB",
            "0xD1220A0Cf47c7B9BE7a2e6ba89F429762E7B9adB",
        ];
        let rskip60_chain_31 = [
            "0x5aAeb6053F3e94c9b9A09F33669435E7EF1BEaEd",
            "0xFb6916095CA1dF60bb79CE92ce3Ea74C37c5D359",
            "0xdbF03B407C01E7cd3cbEa99509D93f8dDDc8C6fB",
            "0xd1220a0CF47c7B9Be7A2E6Ba89f429762E7b9adB",
        ];

        let n = _make_eth_network(Some(30), None, None, None);
        for s in rskip60_chain_30.into_iter() {
            let b = hex_decode(&s[2..]).unwrap();
            let h = address_from_bytes(&b, Some(&n)).unwrap();
            assert_eq!(&h, s);
        }

        let n = _make_eth_network(Some(31), None, None, None);
        for s in rskip60_chain_31.into_iter() {
            let b = hex_decode(&s[2..]).unwrap();
            let h = address_from_bytes(&b, Some(&n)).unwrap();
            assert_eq!(&h, s);
        }
    }
}

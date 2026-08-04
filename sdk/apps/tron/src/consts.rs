pub(crate) const TYPE_URL_TEMPLATE: &str = "type.googleapis.com/protocol.";

// (address_bytes, symbol, decimals)
type TokenDef = (&'static [u8; 21], &'static str, u32);

const TRON_TOKENS: &[TokenDef] = &[
    // SHASTA_USDT_ADDRESS
    (
        b"\x41\x42\xa1\xe3\x9a\xef\xa4\x92\x90\xf2\xb3\xf9\xed\x68\x8d\x7c\xec\xf8\x6c\xd6\xe0",
        "tUSDT",
        6,
    ),
    // USDT_ADDRESS
    (
        b"\x41\xa6\x14\xf8\x03\xb6\xfd\x78\x09\x86\xa4\x2c\x78\xec\x9c\x7f\x77\xe6\xde\xd1\x3c",
        "USDT",
        6,
    ),
    // USDD_ADDRESS
    (
        b"\x41\xe9\x1a\x74\x11\xe5\x6c\xe7\x9e\x83\x57\x05\x70\xf4\x9b\x9f\xc3\x5b\x77\x27\xc5",
        "USDD",
        18,
    ),
    // SUN_ADDRESS
    (
        b"\x41\xb4\xa4\x28\xab\x70\x92\xc2\xf1\x39\x5f\x37\x6c\xe2\x97\x03\x3b\x3b\xb4\x46\xc1",
        "SUN",
        18,
    ),
    // JST_ADDRESS
    (
        b"\x41\x18\xfd\x06\x26\xda\xf3\xaf\x02\x38\x9a\xef\x3e\xd8\x7d\xb9\xc3\x3f\x63\x8f\xfa",
        "JST",
        18,
    ),
    // BTT_ADDRESS
    (
        b"\x41\x03\x20\x17\x41\x1f\x46\x63\xb3\x17\xfe\x77\xc2\x57\xd2\x8d\x5c\xd1\xb2\x6e\x3d",
        "BTT",
        18,
    ),
    //WIN_ADDRESS
    (
        b"\x41\x74\x47\x2e\x7d\x35\x39\x5a\x6b\x5a\xdd\x42\x7e\xec\xb7\xf4\xb6\x2a\xd2\xb0\x71",
        "WIN",
        6,
    ),
    // WBTC_ADDRESS
    (
        b"\x41\xf9\x53\x35\xa4\xd4\x2d\xb4\xb7\x0a\x96\x88\xa3\x93\x27\x9f\x2c\x90\xfa\x10\x25",
        "WBTC",
        8,
    ),
    // ETH_TRON_ADDRESS
    (
        b"\x41\x53\x90\x83\x08\xf4\xaa\x22\x0f\xb1\x0d\x77\x8b\x5d\x1b\x34\x48\x9c\xd6\xed\xfc",
        "ETH",
        18,
    ),
    // USD1_ADDRESS
    (
        b"\x41\x91\xbe\xd8\xe7\x84\x24\x9c\x91\x61\x1e\x61\xc4\x58\x5c\x40\xe2\x1f\xd0\xac\xe2",
        "USD1",
        18,
    ),
    // HTX_ADDRESS
    (
        b"\x41\xca\x03\x03\xe8\xb9\xa7\x38\x12\x17\x77\x11\x6d\xce\xa4\x19\xfe\x52\x4f\x27\x1a",
        "HTX",
        18,
    ),
    // TUSD_ADDRESS
    (
        b"\x41\xce\xbd\xe7\x10\x77\xb8\x30\xb9\x58\xc8\xda\x17\xbc\xdd\xee\xb8\x5d\x0b\xcf\x25",
        "TUSD",
        18,
    ),
    // WBT_ADDRESS
    (
        b"\x41\x40\x3e\x0f\xfc\xa2\x31\xf6\x0f\x8d\x3e\xba\xd4\x26\xf7\x7a\xa6\xb5\x07\x30\x9d",
        "WBT",
        8,
    ),
    // WTRX_ADDRESS
    (
        b"\x41\x89\x1c\xdb\x91\xd1\x49\xf2\x3b\x1a\x45\xd9\xc5\xca\x78\xa8\x8d\x0c\xb4\x4c\x18",
        "WTRX",
        6,
    ),
    // SUNOLD_ADDRESS
    (
        b"\x41\x6b\x51\x51\x32\x03\x59\xec\x18\xb0\x86\x07\xc7\x0a\x3b\x74\x39\xaf\x62\x6a\xa3",
        "SUNOLD",
        18,
    ),
    // AINFT_ADDRESS
    (
        b"\x41\x3d\xfe\x63\x7b\x2b\x9a\xe4\x19\x0a\x45\x8b\x5f\x3e\xfc\x19\x69\xaf\xe2\x78\x19",
        "AINFT",
        6,
    ),
    // STRX_ADDRESS
    (
        b"\x41\xc6\x4e\x69\xac\xde\x1c\x7b\x16\xc2\xa3\xef\xcd\xbb\xda\xa9\x6c\x36\x44\xc2\xb3",
        "sTRX",
        18,
    ),
    // KLEVER_ADDRESS
    (
        b"\x41\xd8\xb8\x08\x98\x56\xce\xd3\x03\x86\x01\xcb\xeb\x1e\x3f\x76\x5c\xab\xc1\x2a\x41",
        "Klever",
        6,
    ),
];

pub(crate) fn token_by_address(address: &[u8]) -> Option<(u32, &'static str)> {
    TRON_TOKENS
        .iter()
        .find(|(addr, _, _)| address == *addr)
        .map(|(_, symbol, decimals)| (*decimals, *symbol))
}

#[cfg(test)]
mod tests {

    fn encode_check(addr_body: &[u8; 20]) -> String {
        let mut full = [0u8; 21];
        full[0] = 0x41;
        full[1..].copy_from_slice(addr_body);
        bs58::encode(full).with_check().into_string()
    }

    // https://shasta.tronscan.org/#/token20/TG3XXyExBkPp9nzdajDZsozEu4BkaSJozs
    #[test]
    fn test_shasta_usdt_address() {
        assert_eq!(
            encode_check(
                b"\x42\xa1\xe3\x9a\xef\xa4\x92\x90\xf2\xb3\xf9\xed\x68\x8d\x7c\xec\xf8\x6c\xd6\xe0"
            ),
            "TG3XXyExBkPp9nzdajDZsozEu4BkaSJozs"
        );
    }

    // https://tronscan.org/#/token20/TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t
    #[test]
    fn test_usdt_address() {
        assert_eq!(
            encode_check(
                b"\xa6\x14\xf8\x03\xb6\xfd\x78\x09\x86\xa4\x2c\x78\xec\x9c\x7f\x77\xe6\xde\xd1\x3c"
            ),
            "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
        );
    }

    // https://tronscan.org/#/token20/TXDk8mbtRbXeYuMNS83CfKPaYYT8XWv9Hz
    #[test]
    fn test_usdd_address() {
        assert_eq!(
            encode_check(
                b"\xe9\x1a\x74\x11\xe5\x6c\xe7\x9e\x83\x57\x05\x70\xf4\x9b\x9f\xc3\x5b\x77\x27\xc5"
            ),
            "TXDk8mbtRbXeYuMNS83CfKPaYYT8XWv9Hz"
        );
    }

    // https://tronscan.org/#/token20/TSSMHYeV2uE9qYH95DqyoCuNCzEL1NvU3S
    #[test]
    fn test_sun_address() {
        assert_eq!(
            encode_check(
                b"\xb4\xa4\x28\xab\x70\x92\xc2\xf1\x39\x5f\x37\x6c\xe2\x97\x03\x3b\x3b\xb4\x46\xc1"
            ),
            "TSSMHYeV2uE9qYH95DqyoCuNCzEL1NvU3S"
        );
    }

    // https://tronscan.org/#/token20/TCFLL5dx5ZJdKnWuesXxi1VPwjLVmWZZy9
    #[test]
    fn test_jst_address() {
        assert_eq!(
            encode_check(
                b"\x18\xfd\x06\x26\xda\xf3\xaf\x02\x38\x9a\xef\x3e\xd8\x7d\xb9\xc3\x3f\x63\x8f\xfa"
            ),
            "TCFLL5dx5ZJdKnWuesXxi1VPwjLVmWZZy9"
        );
    }

    // https://tronscan.org/#/token20/TAFjULxiVgT4qWk6UZwjqwZXTSaGaqnVp4
    #[test]
    fn test_btt_address() {
        assert_eq!(
            encode_check(
                b"\x03\x20\x17\x41\x1f\x46\x63\xb3\x17\xfe\x77\xc2\x57\xd2\x8d\x5c\xd1\xb2\x6e\x3d"
            ),
            "TAFjULxiVgT4qWk6UZwjqwZXTSaGaqnVp4"
        );
    }

    // https://tronscan.org/#/token20/TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7
    #[test]
    fn test_win_address() {
        assert_eq!(
            encode_check(
                b"\x74\x47\x2e\x7d\x35\x39\x5a\x6b\x5a\xdd\x42\x7e\xec\xb7\xf4\xb6\x2a\xd2\xb0\x71"
            ),
            "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7"
        );
    }

    // https://tronscan.org/#/token20/TYhWwKpw43ENFWBTGpzLHn3882f2au7SMi
    #[test]
    fn test_wbtc_address() {
        assert_eq!(
            encode_check(
                b"\xf9\x53\x35\xa4\xd4\x2d\xb4\xb7\x0a\x96\x88\xa3\x93\x27\x9f\x2c\x90\xfa\x10\x25"
            ),
            "TYhWwKpw43ENFWBTGpzLHn3882f2au7SMi"
        );
    }

    // https://tronscan.org/#/token20/THb4CqiFdwNHsWsQCs4JhzwjMWys4aqCbF
    #[test]
    fn test_eth_tron_address() {
        assert_eq!(
            encode_check(
                b"\x53\x90\x83\x08\xf4\xaa\x22\x0f\xb1\x0d\x77\x8b\x5d\x1b\x34\x48\x9c\xd6\xed\xfc"
            ),
            "THb4CqiFdwNHsWsQCs4JhzwjMWys4aqCbF"
        );
    }

    // https://tronscan.org/#/token20/TPFqcBAaaUMCSVRCqPaQ9QnzKhmuoLR6Rc
    #[test]
    fn test_usd1_address() {
        assert_eq!(
            encode_check(
                b"\x91\xbe\xd8\xe7\x84\x24\x9c\x91\x61\x1e\x61\xc4\x58\x5c\x40\xe2\x1f\xd0\xac\xe2"
            ),
            "TPFqcBAaaUMCSVRCqPaQ9QnzKhmuoLR6Rc"
        );
    }

    // https://tronscan.org/#/token20/TUPM7K8REVzD2UdV4R5fe5M8XbnR2DdoJ6
    #[test]
    fn test_htx_address() {
        assert_eq!(
            encode_check(
                b"\xca\x03\x03\xe8\xb9\xa7\x38\x12\x17\x77\x11\x6d\xce\xa4\x19\xfe\x52\x4f\x27\x1a"
            ),
            "TUPM7K8REVzD2UdV4R5fe5M8XbnR2DdoJ6"
        );
    }

    // https://tronscan.org/#/token20/TUpMhErZL2fhh4sVNULAbNKLokS4GjC1F4
    #[test]
    fn test_tusd_address() {
        assert_eq!(
            encode_check(
                b"\xce\xbd\xe7\x10\x77\xb8\x30\xb9\x58\xc8\xda\x17\xbc\xdd\xee\xb8\x5d\x0b\xcf\x25"
            ),
            "TUpMhErZL2fhh4sVNULAbNKLokS4GjC1F4"
        );
    }

    // https://tronscan.org/#/token20/TFptbWaARrWTX5Yvy3gNG5Lm8BmhPx82Bt
    #[test]
    fn test_wbt_address() {
        assert_eq!(
            encode_check(
                b"\x40\x3e\x0f\xfc\xa2\x31\xf6\x0f\x8d\x3e\xba\xd4\x26\xf7\x7a\xa6\xb5\x07\x30\x9d"
            ),
            "TFptbWaARrWTX5Yvy3gNG5Lm8BmhPx82Bt"
        );
    }

    // https://tronscan.org/#/token20/TNUC9Qb1rRpS5CbWLmNMxXBjyFoydXjWFR
    #[test]
    fn test_wtrx_address() {
        assert_eq!(
            encode_check(
                b"\x89\x1c\xdb\x91\xd1\x49\xf2\x3b\x1a\x45\xd9\xc5\xca\x78\xa8\x8d\x0c\xb4\x4c\x18"
            ),
            "TNUC9Qb1rRpS5CbWLmNMxXBjyFoydXjWFR"
        );
    }

    // https://tronscan.org/#/token20/TKkeiboTkxXKJpbmVFbv4a8ov5rAfRDMf9
    #[test]
    fn test_sunold_address() {
        assert_eq!(
            encode_check(
                b"\x6b\x51\x51\x32\x03\x59\xec\x18\xb0\x86\x07\xc7\x0a\x3b\x74\x39\xaf\x62\x6a\xa3"
            ),
            "TKkeiboTkxXKJpbmVFbv4a8ov5rAfRDMf9"
        );
    }

    // https://tronscan.org/#/token20/TFczxzPhnThNSqr5by8tvxsdCFRRz6cPNq
    #[test]
    fn test_ainft_address() {
        assert_eq!(
            encode_check(
                b"\x3d\xfe\x63\x7b\x2b\x9a\xe4\x19\x0a\x45\x8b\x5f\x3e\xfc\x19\x69\xaf\xe2\x78\x19"
            ),
            "TFczxzPhnThNSqr5by8tvxsdCFRRz6cPNq"
        );
    }

    // https://tronscan.org/#/token20/TU3kjFuhtEo42tsCBtfYUAZxoqQ4yuSLQ5
    #[test]
    fn test_strx_address() {
        assert_eq!(
            encode_check(
                b"\xc6\x4e\x69\xac\xde\x1c\x7b\x16\xc2\xa3\xef\xcd\xbb\xda\xa9\x6c\x36\x44\xc2\xb3"
            ),
            "TU3kjFuhtEo42tsCBtfYUAZxoqQ4yuSLQ5"
        );
    }

    // https://tronscan.org/#/token20/TVj7RNVHy6thbM7BWdSe9G6gXwKhjhdNZS
    #[test]
    fn test_klever_address() {
        assert_eq!(
            encode_check(
                b"\xd8\xb8\x08\x98\x56\xce\xd3\x03\x86\x01\xcb\xeb\x1e\x3f\x76\x5c\xab\xc1\x2a\x41"
            ),
            "TVj7RNVHy6thbM7BWdSe9G6gXwKhjhdNZS"
        );
    }
}

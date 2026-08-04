use crate::alloc_types::String;

// Smart contract 'data' field lengths in bytes
pub(crate) const SC_FUNC_SIG_BYTES: usize = 4;
pub(crate) const SC_ARGUMENT_BYTES: usize = 32;
pub(crate) const SC_ARGUMENT_ADDRESS_BYTES: usize = 20;

// Compile-time assertion
const _: () = assert!(SC_ARGUMENT_ADDRESS_BYTES <= SC_ARGUMENT_BYTES);

// Known ERC-20 functions
pub(crate) const SC_FUNC_SIG_TRANSFER: [u8; 4] = [0xa9, 0x05, 0x9c, 0xbb];
pub(crate) const SC_FUNC_SIG_APPROVE: [u8; 4] = [0x09, 0x5e, 0xa7, 0xb3];

// Approve known addresses
// This should eventually grow into a more comprehensive database and stored in some other way,
// but for now let's just keep a few known addresses here!
const ADDR_UNISWAP_V3_ROUTER: [u8; 20] = [
    0xe5, 0x92, 0x42, 0x7a, 0x0a, 0xec, 0xe9, 0x2d, 0xe3, 0xed, 0xee, 0x1f, 0x18, 0xe0, 0x15, 0x7c,
    0x05, 0x86, 0x15, 0x64,
];
const ADDR_1INCH_V6: [u8; 20] = [
    0x11, 0x11, 0x11, 0x12, 0x54, 0x21, 0xca, 0x6d, 0xc4, 0x52, 0xd2, 0x89, 0x31, 0x42, 0x80, 0xa0,
    0xf8, 0x84, 0x2a, 0x65,
];
const ADDR_LIFI_DIAMOND: [u8; 20] = [
    0x12, 0x31, 0xde, 0xb6, 0xf5, 0x74, 0x9e, 0xf6, 0xce, 0x69, 0x43, 0xa2, 0x75, 0xa1, 0xd3, 0xe7,
    0x48, 0x6f, 0x4e, 0xae,
];

pub const APPROVE_KNOWN_ADDRESSES: [([u8; 20], &str); 3] = [
    (ADDR_UNISWAP_V3_ROUTER, "Uniswap V3 Router"),
    (ADDR_1INCH_V6, "1inch Aggregation Router V6"),
    (ADDR_LIFI_DIAMOND, "LiFI Diamond"),
];

pub fn get_approve_known_address(addr: &[u8]) -> Option<String> {
    APPROVE_KNOWN_ADDRESSES
        .iter()
        .find(|(a, _)| a.as_slice() == addr)
        .map(|(_, name)| (*name).into())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::strutil::hex_decode;

    // Verify constants match the hex strings they replaced
    #[test]
    fn test_sc_func_sig_constants() {
        assert_eq!(
            SC_FUNC_SIG_TRANSFER,
            hex_decode("a9059cbb").unwrap().as_slice()
        );
        assert_eq!(
            SC_FUNC_SIG_APPROVE,
            hex_decode("095ea7b3").unwrap().as_slice()
        );
    }

    #[test]
    fn test_approve_known_address_constants() {
        assert_eq!(
            &ADDR_UNISWAP_V3_ROUTER[..],
            hex_decode("e592427a0aece92de3edee1f18e0157c05861564")
                .unwrap()
                .as_slice()
        );
        assert_eq!(
            &ADDR_1INCH_V6[..],
            hex_decode("111111125421cA6dc452d289314280a0f8842A65")
                .unwrap()
                .as_slice()
        );
        assert_eq!(
            &ADDR_LIFI_DIAMOND[..],
            hex_decode("1231DEB6f5749EF6cE6943a275A1D3E7486F4EaE")
                .unwrap()
                .as_slice()
        );
    }
}

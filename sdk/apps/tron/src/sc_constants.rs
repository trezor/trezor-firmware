// Smart contract 'data' field lengths in bytes
pub(crate) const SC_FUNC_SIG_BYTES: usize = 4;
pub(crate) const SC_ARGUMENT_BYTES: usize = 32;
pub(crate) const SC_ARGUMENT_ADDRESS_BYTES: usize = 20;

// Compile-time assertion
const _: () = assert!(SC_ARGUMENT_ADDRESS_BYTES <= SC_ARGUMENT_BYTES);

// Known TRC-20/ERC-20 functions
pub(crate) const SC_FUNC_SIG_TRANSFER: [u8; 4] = [0xa9, 0x05, 0x9c, 0xbb];
pub(crate) const SC_FUNC_SIG_APPROVE: [u8; 4] = [0x09, 0x5e, 0xa7, 0xb3];

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
}

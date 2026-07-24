pub use trezor_crc32::{Crc32, digest};

#[cfg(test)]
mod test {
    use super::*;
    use crate::strutil::hexlify;

    const CRC32_VECTORS: &[(&[u8], &[u8])] = &[
        (b"", b"00000000"),
        (b"a", b"e8b7be43"),
        (b"abc", b"352441c2"),
        (b"message digest", b"20159d7f"),
        (b"abcdefghijklmnopqrstuvwxyz", b"4c2750bd"),
        (
            b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789",
            b"1fc2e6d2",
        ),
        (
            b"12345678901234567890123456789012345678901234567890123456789012345678901234567890",
            b"7ca94a72",
        ),
    ];

    fn hexdigest(data: &[u8]) -> [u8; 8] {
        let mut out_hex = [0u8; 8];
        let digest = digest(data);
        hexlify(&digest, &mut out_hex);
        out_hex
    }

    #[test]
    fn test_no_update() {
        let out = Crc32::new().finalize();
        let mut out_hex = [0u8; 8];
        hexlify(&out, &mut out_hex);

        assert_eq!(out_hex, *b"00000000");
    }

    #[test]
    fn test_vectors() {
        for (data, expected) in CRC32_VECTORS {
            let out_hex = hexdigest(data);
            assert_eq!(out_hex, *expected);
        }
    }
}

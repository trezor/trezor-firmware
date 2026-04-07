pub struct Crc32 {
    value: u32,
}

static CRC32TAB: [u32; 16] = [
    0x00000000, 0x1db71064, 0x3b6e20c8, 0x26d930ac, 0x76dc4190, 0x6b6b51f4, 0x4db26158, 0x5005713c,
    0xedb88320, 0xf00f9344, 0xd6d6a3e8, 0xcb61b38c, 0x9b64c2b0, 0x86d3d2d4, 0xa00ae278, 0xbdbdf21c,
];

impl Crc32 {
    pub fn new() -> Self {
        Self { value: u32::MAX }
    }

    pub fn update(mut self, data: &[u8]) -> Self {
        for b in data {
            self.value ^= *b as u32;
            self.value = CRC32TAB[(self.value & 0x0f) as usize] ^ (self.value >> 4);
            self.value = CRC32TAB[(self.value & 0x0f) as usize] ^ (self.value >> 4);
        }
        self
    }

    pub fn finalize(self) -> [u8; 4] {
        let inverted = self.value ^ u32::MAX;
        inverted.to_be_bytes()
    }
}

pub fn digest(data: &[u8]) -> [u8; 4] {
    Crc32::new().update(data).finalize()
}

#[cfg(test)]
mod test {
    use crate::strutil::hexlify;

    use super::*;

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

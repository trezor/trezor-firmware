#![allow(dead_code)]

pub struct Crc32 {
    value: u32,
}

static CRC32TAB: [u32; 16] = [
    0x00000000, 0x1db71064, 0x3b6e20c8, 0x26d930ac, 0x76dc4190, 0x6b6b51f4, 0x4db26158, 0x5005713c,
    0xedb88320, 0xf00f9344, 0xd6d6a3e8, 0xcb61b38c, 0x9b64c2b0, 0x86d3d2d4, 0xa00ae278, 0xbdbdf21c,
];

pub const CHECKSUM_LEN: usize = 4;

impl Crc32 {
    pub fn new() -> Self {
        Self { value: u32::MAX }
    }

    pub fn update(&mut self, data: &[u8]) {
        for b in data {
            self.value ^= *b as u32;
            self.value = CRC32TAB[(self.value & 0x0f) as usize] ^ (self.value >> 4);
            self.value = CRC32TAB[(self.value & 0x0f) as usize] ^ (self.value >> 4);
        }
    }

    pub fn finalize(&self) -> [u8; CHECKSUM_LEN] {
        let inverted = self.value ^ u32::MAX;
        inverted.to_be_bytes()
    }
}

pub fn digest(data: &[u8]) -> [u8; CHECKSUM_LEN] {
    let mut crc = Crc32::new();
    crc.update(data);
    crc.finalize()
}

pub fn verify_payload(buffer: &[u8]) -> Option<&[u8]> {
    let (payload, digest_in) = buffer.split_last_chunk::<CHECKSUM_LEN>()?;
    let digest_computed = digest(payload);
    (digest_computed == *digest_in).then_some(payload)
}

pub fn verify(data: &[u8]) -> bool {
    verify_payload(data).is_some()
}

#[cfg(test)]
mod test {
    use super::*;

    const CRC32_VECTORS: &[(&[u8], &str)] = &[
        (b"", "00000000"),
        (b"a", "e8b7be43"),
        (b"abc", "352441c2"),
        (b"message digest", "20159d7f"),
        (b"abcdefghijklmnopqrstuvwxyz", "4c2750bd"),
        (
            b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789",
            "1fc2e6d2",
        ),
        (
            b"12345678901234567890123456789012345678901234567890123456789012345678901234567890",
            "7ca94a72",
        ),
    ];

    #[test]
    fn test_no_update() {
        let out = Crc32::new().finalize();
        let out_hex = hex::encode(out);
        assert_eq!(out_hex, "00000000");
    }

    #[test]
    fn test_vectors() {
        for (data, expected) in CRC32_VECTORS {
            let out_hex = hex::encode(digest(data));
            assert_eq!(out_hex, *expected);
        }
    }
}

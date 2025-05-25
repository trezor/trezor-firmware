/// Compute CRC-16-ITU-T over `data`, starting from `seed`.
pub fn crc16_itu_t(mut seed: u16, data: &[u8]) -> u16 {
    for &byte in data {
        // swap high/low byte:
        seed = seed.rotate_left(8);
        // mix in next input byte
        seed ^= byte as u16;
        // apply the ITU-T polynomial bitwise mix
        seed ^= (seed & 0x00FF) >> 4;
        seed ^= seed << 12;
        seed ^= (seed & 0x00FF) << 5;
    }
    seed
}

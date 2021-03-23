// https://developers.google.com/protocol-buffers/docs/encoding#signed_integers

pub fn to_unsigned(sint: i64) -> u64 {
    ((sint << 1) ^ (sint >> 63)) as u64
}

pub fn to_signed(uint: u64) -> i64 {
    ((uint >> 1) as i64) ^ (-((uint & 1) as i64))
}

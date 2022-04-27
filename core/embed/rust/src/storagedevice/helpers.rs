use heapless::String;

pub fn hexlify_bytes<const N: usize>(bytes: &[u8]) -> String<N> {
    let mut buf = String::<N>::from("");
    for byte in bytes {
        fn hex_from_digit(num: u8) -> char {
            if num < 10 {
                (b'0' + num) as char
            } else {
                (b'A' + num - 10) as char
            }
        }
        buf.push(hex_from_digit(byte / 16)).unwrap();
        buf.push(hex_from_digit(byte % 16)).unwrap();
    }
    buf
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_hexlify_bytes() {
        let bytes: &[u8; 6] = &[52, 241, 6, 151, 173, 74];
        let result: String<12> = hexlify_bytes(bytes);
        assert_eq!(result, String::<12>::from("34F10697AD4A"));
    }
}

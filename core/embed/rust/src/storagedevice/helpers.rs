use heapless::String;

const FLAG_PUBLIC: u8 = 0x80;
const FLAGS_WRITE: u8 = 0xC0;

pub fn get_appkey(app: u8, key: u8, is_public: bool) -> u16 {
    let app = if is_public { app | FLAG_PUBLIC } else { app };
    ((app as u16) << 8) | key as u16
}

pub fn get_appkey_u2f(app: u8, key: u8, writable_locked: bool) -> u16 {
    let app = if writable_locked {
        app | FLAGS_WRITE
    } else {
        app | FLAG_PUBLIC
    };
    ((app as u16) << 8) | key as u16
}

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
        // TODO: error handling?
        buf.push(hex_from_digit(byte / 16)).unwrap();
        buf.push(hex_from_digit(byte % 16)).unwrap();
    }
    buf
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_get_appkey() {
        let result = get_appkey(0x01, 0x11, false);
        assert_eq!(result, 0x0111);
    }

    #[test]
    fn test_get_appkey_public() {
        let result = get_appkey(0x01, 0x11, true);
        assert_eq!(result, 0x8111);
    }

    #[test]
    fn test_get_appkey_u2f_writable_locked() {
        let result = get_appkey_u2f(0x01, 0x09, true);
        assert_eq!(result, 0xC109);
    }

    #[test]
    fn test_get_appkey_u2f_not_writable_locked() {
        let result = get_appkey_u2f(0x01, 0x09, false);
        assert_eq!(result, 0x8109);
    }

    #[test]
    fn test_hexlify_bytes() {
        let bytes: &[u8; 6] = &[52, 241, 6, 151, 173, 74];
        let result: String<12> = hexlify_bytes(bytes);
        assert_eq!(result, String::<12>::from("34F10697AD4A"));
    }
}

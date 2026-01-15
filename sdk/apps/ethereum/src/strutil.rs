#[cfg(not(test))]
use alloc::{
    string::{String, ToString},
    vec::Vec,
};
use core::{convert::Infallible, result::Result};
#[cfg(test)]
use std::{
    string::{String, ToString},
    vec::Vec,
};
use trezor_app_sdk::unwrap;
use ufmt::uWrite;
pub struct StringWriter(String);
impl StringWriter {
    pub fn new() -> Self {
        Self(String::new())
    }
    pub fn to_string(self) -> String {
        self.0
    }
}

impl uWrite for StringWriter {
    type Error = Infallible;
    fn write_str(&mut self, s: &str) -> Result<(), Self::Error> {
        self.0.push_str(s);
        Ok(())
    }
}

// Returns an `alloc::string::String` using `ufmt::uwrite!`
// from https://docs.rs/ufmt/latest/ufmt/
// like `std::format!` it returns a `String` but uses `uwrite!`
// instead of `write!`
#[macro_export]
macro_rules! uformat {
    (len:$len:expr, $($tt:tt)*) => {
        {
            let mut s = heapless::String::<$len>::new();
            use trezor_app_sdk::unwrap;
            unwrap!(ufmt::uwrite!(&mut s, $($tt)*));
            s
        }
    };
    ($($tt:tt)*) => {
        {
            use trezor_app_sdk::unwrap;
            let mut s = $crate::strutil::StringWriter::new();
            unwrap!(ufmt::uwrite!(&mut s, $($tt)*));
            s.to_string()
        }
    };
}

pub fn hex_encode(bytes: &[u8]) -> String {
    let mut s = StringWriter::new();
    for byte in bytes {
        unwrap!(ufmt::uwrite!(&mut s, "{:02x}", *byte));
    }
    s.to_string()
}

pub fn hex_decode(hex: &str) -> Result<Vec<u8>, ()> {
    if hex.len() % 2 != 0 {
        return Err(());
    }

    let mut bytes = Vec::with_capacity(hex.len() / 2);
    let chars: Vec<char> = hex.chars().collect();

    for i in (0..chars.len()).step_by(2) {
        let high = chars[i].to_digit(16).ok_or(())?;
        let low = chars[i + 1].to_digit(16).ok_or(())?;
        bytes.push(((high << 4) | low) as u8);
    }

    Ok(bytes)
}

pub fn format_plural_english(count: u32, singular: &str) -> String {
    let mut plural = singular.to_string();
    if count != 1 {
        // candy -> candies, but key -> keys
        if singular.ends_with('y')
            && !matches!(
                singular.chars().nth_back(1),
                Some('a' | 'e' | 'i' | 'o' | 'u' | 'y')
            )
        {
            plural.pop(); // remove trailing 'y'
            plural.push_str("ies");
        } else if matches!(singular.chars().last(), Some('h' | 's' | 'x' | 'z')) {
            plural.push_str("es");
        } else {
            plural.push('s');
        }
    }

    uformat!("{} {}", count, plural.as_str())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_hex_encode_empty() {
        let result = hex_encode(&[]);
        assert_eq!(result, "");
    }

    #[test]
    fn test_hex_encode_single_byte() {
        let result = hex_encode(&[0xAB]);
        assert_eq!(result, "ab");
    }

    #[test]
    fn test_hex_encode_multiple_bytes() {
        let result = hex_encode(&[0x00, 0xFF, 0xAB, 0xCD]);
        assert_eq!(result, "00ffabcd");
    }

    #[test]
    fn test_hex_encode_all_zeros() {
        let result = hex_encode(&[0x00, 0x00, 0x00]);
        assert_eq!(result, "000000");
    }

    #[test]
    fn test_hex_decode_empty() {
        let result = hex_decode("");
        assert_eq!(result, Ok(vec![]));
    }

    #[test]
    fn test_hex_decode_single_byte() {
        let result = hex_decode("ab");
        assert_eq!(result, Ok(vec![0xAB]));
    }

    #[test]
    fn test_hex_decode_multiple_bytes() {
        let result = hex_decode("00ffabcd");
        assert_eq!(result, Ok(vec![0x00, 0xFF, 0xAB, 0xCD]));
    }

    #[test]
    fn test_hex_decode_uppercase() {
        let result = hex_decode("ABCD");
        assert_eq!(result, Ok(vec![0xAB, 0xCD]));
    }

    #[test]
    fn test_hex_decode_mixed_case() {
        let result = hex_decode("AaBbCc");
        assert_eq!(result, Ok(vec![0xAA, 0xBB, 0xCC]));
    }

    #[test]
    fn test_hex_decode_invalid_characters() {
        // Test various invalid characters
        assert_eq!(hex_decode("GH"), Err(()));
        assert_eq!(hex_decode("zz"), Err(()));
        assert_eq!(hex_decode("!!"), Err(()));
        assert_eq!(hex_decode("@#"), Err(()));
        assert_eq!(hex_decode("--"), Err(()));
    }

    #[test]
    fn test_hex_decode_with_spaces() {
        assert_eq!(hex_decode("ab cd"), Err(()));
        assert_eq!(hex_decode(" abcd"), Err(()));
        assert_eq!(hex_decode("abcd "), Err(()));
    }

    #[test]
    fn test_hex_decode_with_prefix() {
        // Common prefixes that should fail
        assert_eq!(hex_decode("0xabcd"), Err(()));
        assert_eq!(hex_decode("0X1234"), Err(()));
    }

    #[test]
    fn test_hex_decode_odd_length() {
        assert_eq!(hex_decode("a"), Err(()));
        assert_eq!(hex_decode("abc"), Err(()));
        assert_eq!(hex_decode("abcdf"), Err(()));
    }

    #[test]
    fn test_hex_decode_special_characters() {
        assert_eq!(hex_decode("\n\n"), Err(()));
        assert_eq!(hex_decode("\t\t"), Err(()));
        assert_eq!(hex_decode("ab\ncd"), Err(()));
    }

    #[test]
    fn test_hex_decode_unicode() {
        assert_eq!(hex_decode("äb"), Err(()));
        assert_eq!(hex_decode("αβ"), Err(()));
    }

    #[test]
    fn test_hex_encode_decode_roundtrip() {
        let original = vec![0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC, 0xDE, 0xF0];
        let encoded = hex_encode(&original);
        let decoded = hex_decode(&encoded).expect("decode failed");
        assert_eq!(decoded, original);
    }
}

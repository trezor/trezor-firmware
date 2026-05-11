#[cfg(not(test))]
use alloc::string::String;
use core::{convert::Infallible, result::Result};
#[cfg(test)]
use std::string::String;
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
}

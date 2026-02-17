extern crate alloc;

use alloc::string::String;
use alloc::vec::Vec;
use core::convert::Infallible;
use core::result::Result;
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

// pub fn hex_encode(bytes: &[u8]) -> String {
//     let mut result = String::new();
//     for byte in bytes {
//         // Manually append hex digits
//         let high = (byte >> 4) & 0x0F;
//         let low = byte & 0x0F;
//         result.push(char::from_digit(high as u32, 16).unwrap());
//         result.push(char::from_digit(low as u32, 16).unwrap());
//     }
//     result
// }

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

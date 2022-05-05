use heapless::String;

use cstr_core::CStr;

pub trait ResultExt {
    fn assert_if_debugging_ui(self, message: &str);
}

impl<T, E> ResultExt for Result<T, E> {
    fn assert_if_debugging_ui(self, #[allow(unused)] message: &str) {
        #[cfg(feature = "ui_debug")]
        if self.is_err() {
            panic!("{}", message);
        }
    }
}

pub fn u32_to_str(num: u32, buffer: &mut [u8]) -> Option<&str> {
    let mut i = 0;
    let mut num = num;

    while num > 0 && i < buffer.len() {
        buffer[i] = b'0' + ((num % 10) as u8);
        num /= 10;
        i += 1;
    }
    match i {
        0 => Some("0"),
        _ if num > 0 => None,
        _ => {
            let result = &mut buffer[..i];
            result.reverse();
            Some(core::str::from_utf8(result).unwrap())
        }
    }
}

pub unsafe fn from_c_str(c_str: *const cty::c_char) -> Option<&'static str> {
    unsafe {
        let bytes = CStr::from_ptr(c_str).to_bytes();
        if bytes.is_ascii() {
            Some(core::str::from_utf8_unchecked(bytes))
        } else {
            None
        }
    }
}

pub unsafe fn from_c_array(c_str: *const cty::c_char, len: usize) -> Option<&'static str> {
    unsafe {
        let slice = core::slice::from_raw_parts(c_str as *const u8, len);
        if slice.is_ascii() {
            Some(core::str::from_utf8_unchecked(slice))
        } else {
            None
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn u32_to_str_valid() {
        let testcases = [0, 1, 9, 10, 11, 999, u32::MAX];
        let mut b = [0; 10];

        for test in testcases {
            let converted = u32_to_str(test, &mut b).unwrap();
            let s = test.to_string();
            assert_eq!(converted, s);
        }
    }

    #[test]
    fn u32_to_str_small_buffer() {
        let testcases = [1000, 31337, u32::MAX];
        let mut b = [0; 3];

        for test in testcases {
            let converted = u32_to_str(test, &mut b);
            assert_eq!(converted, None)
        }
    }
}

/// Convert char to a String of chosen length.
pub fn char_to_string<const L: usize>(ch: char) -> String<L> {
    let mut s = String::new();
    s.push(ch).unwrap();
    s
}

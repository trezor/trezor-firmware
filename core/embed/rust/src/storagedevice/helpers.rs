use crate::{error::Error, trezorhal::secbool};
use cstr_core::cstr;
use heapless::String;

extern "C" {
    // storage.h
    fn storage_has(key: u16) -> secbool::Secbool;
    fn storage_delete(key: u16) -> secbool::Secbool;
    fn storage_get(key: u16, val: *const u8, max_len: u16, len: *mut u16) -> secbool::Secbool;
    fn storage_set(key: u16, val: *const u8, len: u16) -> secbool::Secbool;
}

const FLAG_PUBLIC: u8 = 0x80;
const FLAGS_WRITE: u8 = 0xC0;

// TODO: decide on naming conventions of these wrappers (so far "_rs" suffix)

pub fn storage_has_rs(key: u16) -> bool {
    secbool::TRUE == unsafe { storage_has(key) }
}

pub fn storage_delete_rs(key: u16) -> Result<(), Error> {
    let result = unsafe { storage_delete(key) };
    if result != secbool::TRUE {
        Err(Error::ValueError(cstr!(
            "Could not delete value in storage"
        )))
    } else {
        Ok(())
    }
}

pub fn storage_delete_safe_rs(key: u16) -> Result<(), Error> {
    // If there is nothing, storage_delete() would return false
    if !storage_has_rs(key) {
        Ok(())
    } else {
        storage_delete_rs(key)
    }
}

pub fn storage_get_rs<const N: usize>(key: u16, buf: &mut [u8; N]) -> Option<u16> {
    assert!(N <= u16::MAX as usize);
    let mut len = 0;
    let result = unsafe { storage_get(key, buf.as_mut_ptr(), N as u16, &mut len) };
    if result != secbool::TRUE {
        None
    } else {
        Some(len)
    }
}

pub fn storage_set_rs(key: u16, buf: &[u8]) -> Result<(), Error> {
    assert!(buf.len() <= u16::MAX as usize);
    let result = unsafe { storage_set(key, buf.as_ptr(), buf.len() as u16) };
    if result != secbool::TRUE {
        Err(Error::ValueError(cstr!("Could not save value to storage")))
    } else {
        Ok(())
    }
}

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

pub fn hexlify_bytes(bytes: &[u8]) -> String<64> {
    let mut buf = String::<64>::from("");
    for byte in bytes {
        fn hex_from_digit(num: u8) -> char {
            if num < 10 {
                (b'0' + num) as char
            } else {
                (b'A' + num - 10) as char
            }
        }
        // TODO: error handling
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
        let result = hexlify_bytes(bytes);
        assert_eq!(result, String::<64>::from("34F10697AD4A"));
    }
}

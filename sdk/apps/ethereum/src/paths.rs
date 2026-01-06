const HARDENED: u32 = 0x80000000;
const MAX_PATH_STR_LEN: usize = 256; // "m/44'/0'/0'/0/0" with margin

/// Convert BIP-32 path to string representation (e.g., "m/44'/0'/0'/0/0")
pub fn address_n_to_str(address_n: &[u32]) -> alloc::string::String {
    use alloc::string::String;
    use trezor_app_sdk::util::SliceWriter;
    use ufmt::uWrite;

    let mut buf = [0u8; MAX_PATH_STR_LEN];
    let mut writer = SliceWriter::new(&mut buf);

    if address_n.is_empty() {
        let _ = ufmt::uwrite!(writer, "m");
        return String::from(writer.as_ref());
    }

    let _ = ufmt::uwrite!(writer, "m");
    for (idx, &i) in address_n.iter().enumerate() {
        let _ = ufmt::uwrite!(writer, "/");
        if i & HARDENED != 0 {
            let _ = ufmt::uwrite!(writer, "{}'", i ^ HARDENED);
        } else {
            let _ = ufmt::uwrite!(writer, "{}", i);
        }
    }

    String::from(writer.as_ref())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_empty_path() {
        assert_eq!(address_n_to_str(&[]), "m");
    }

    #[test]
    fn test_hardened_path() {
        let path = [0x80000000 + 44, 0x80000000 + 0, 0x80000000 + 0];
        assert_eq!(address_n_to_str(&path), "m/44'/0'/0'");
    }

    #[test]
    fn test_mixed_path() {
        let path = [0x80000000 + 44, 0x80000000 + 0, 0x80000000 + 0, 0, 0];
        assert_eq!(address_n_to_str(&path), "m/44'/0'/0'/0/0");
    }
}

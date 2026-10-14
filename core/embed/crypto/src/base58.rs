//! Base58 and Base58Check (double SHA-256 checksum) encoding.
//!
//! Wraps trezor-crypto's `base58.c`, which sizes its scratch buffers on the
//! stack from the input length. Inputs are therefore capped at
//! [`MAX_DATA_LEN`] bytes, which `base58_encode_check()` and
//! `base58_decode_check()` enforce anyway.

use rtl::CSlice;

use super::{Error, ffi};

/// Maximum length of the data to encode, or of the decoded data.
pub const MAX_DATA_LEN: usize = 128;

/// Maximum length of an encoded string: [`MAX_DATA_LEN`] bytes plus the
/// 4-byte checksum, at `log(256) / log(58) < 1.38` characters per byte.
pub const MAX_ENCODED_LEN: usize = (MAX_DATA_LEN + 4) * 138 / 100 + 1;

/// Buffer for an encoded string, including the C NUL terminator.
pub type EncodeBuffer = [u8; MAX_ENCODED_LEN + 1];

/// Buffer for decoded data.
pub type DecodeBuffer = [u8; MAX_DATA_LEN];

const CHECKSUM_LEN: usize = 4;

/// Base58-encodes `data` into `buffer`.
pub fn encode<'a>(data: &[u8], buffer: &'a mut EncodeBuffer) -> Result<&'a str, Error> {
    if data.len() > MAX_DATA_LEN {
        return Err(Error::InvalidParams);
    }
    let data = CSlice::from(data);
    // `b58enc` takes the buffer size and returns the written length, both
    // including the NUL terminator.
    let mut len = buffer.len();
    // SAFETY: `buffer` is valid for writes of `len` bytes, and `data` for
    // reads of `data.len()` bytes; the C code keeps neither pointer.
    let ok = unsafe {
        ffi::b58enc(
            buffer.as_mut_ptr().cast(),
            &mut len,
            data.ptr().cast(),
            data.len(),
        )
    };
    if !ok {
        return Err(Error::InvalidParams);
    }
    Ok(as_ascii_str(&buffer[..len - 1]))
}

/// Base58Check-encodes `data` into `buffer`.
pub fn encode_check<'a>(data: &[u8], buffer: &'a mut EncodeBuffer) -> Result<&'a str, Error> {
    if data.len() > MAX_DATA_LEN {
        return Err(Error::InvalidParams);
    }
    let data = CSlice::from(data);
    // SAFETY: as in `encode`. Returns the written length including the NUL
    // terminator, or 0 on failure.
    let len = unsafe {
        ffi::base58_encode_check(
            data.ptr(),
            data.len(),
            ffi::HasherType::HASHER_SHA2D,
            buffer.as_mut_ptr().cast(),
            buffer.len(),
        )
    };
    if len == 0 {
        return Err(Error::InvalidParams);
    }
    Ok(as_ascii_str(&buffer[..len - 1]))
}

/// Decodes base58 `string` into `buffer`, returning the decoded part of it.
pub fn decode<'a>(string: &str, buffer: &'a mut DecodeBuffer) -> Result<&'a [u8], Error> {
    let mut c_string = [0u8; MAX_ENCODED_LEN + 1];
    let c_string = to_c_string(string, &mut c_string)?;
    // `b58tobin` takes the buffer size and returns the decoded length. The
    // decoded data is right-aligned in the buffer.
    let mut len = buffer.len();
    // SAFETY: `buffer` is valid for writes of `len` bytes, and `c_string` is
    // NUL-terminated; the C code keeps neither pointer.
    let ok = unsafe { ffi::b58tobin(buffer.as_mut_ptr().cast(), &mut len, c_string) };
    if !ok {
        return Err(Error::InvalidEncoding);
    }
    Ok(&buffer[buffer.len() - len..])
}

/// Decodes Base58Check `string` into `buffer` and verifies its checksum,
/// returning the decoded data without the checksum.
pub fn decode_check<'a>(string: &str, buffer: &'a mut DecodeBuffer) -> Result<&'a [u8], Error> {
    let mut c_string = [0u8; MAX_ENCODED_LEN + 1];
    let c_string = to_c_string(string, &mut c_string)?;
    let mut decoded = [0u8; MAX_DATA_LEN + CHECKSUM_LEN];
    let mut len = decoded.len();
    // SAFETY: as in `decode`.
    let ok = unsafe { ffi::b58tobin(decoded.as_mut_ptr().cast(), &mut len, c_string) };
    if !ok {
        return Err(Error::InvalidEncoding);
    }
    let decoded = &decoded[decoded.len() - len..];
    // Done here rather than with `base58_decode_check()`, whose 0 return
    // can't tell an error from empty data.
    // SAFETY: `decoded` is valid for reads of `decoded.len()` bytes, and
    // `c_string` is the NUL-terminated string it was decoded from.
    let res = unsafe {
        ffi::b58check(
            decoded.as_ptr().cast(),
            decoded.len(),
            ffi::HasherType::HASHER_SHA2D,
            c_string,
        )
    };
    if res < 0 {
        return Err(Error::InvalidEncoding);
    }
    let data = &decoded[..decoded.len() - CHECKSUM_LEN];
    buffer[..data.len()].copy_from_slice(data);
    Ok(&buffer[..data.len()])
}

/// Copies `string` into `buffer` with a NUL terminator, for the C decoder.
fn to_c_string(
    string: &str,
    buffer: &mut [u8; MAX_ENCODED_LEN + 1],
) -> Result<*const cty::c_char, Error> {
    // Longer strings can't decode to at most `MAX_DATA_LEN` (+ checksum)
    // bytes anyway. An inner NUL would make C silently decode only a prefix.
    if string.len() > MAX_ENCODED_LEN || string.bytes().any(|b| b == 0) {
        return Err(Error::InvalidEncoding);
    }
    buffer[..string.len()].copy_from_slice(string.as_bytes());
    buffer[string.len()] = 0;
    Ok(buffer.as_ptr().cast())
}

fn as_ascii_str(bytes: &[u8]) -> &str {
    // The base58 alphabet is ASCII.
    debug_assert!(bytes.is_ascii());
    // SAFETY: ASCII is a subset of UTF-8.
    unsafe { core::str::from_utf8_unchecked(bytes) }
}

#[cfg(test)]
mod test {
    use super::*;

    #[test]
    fn test_encode_decode() {
        let vectors: &[(&[u8], &str)] = &[
            (b"", ""),
            (&[0], "1"),
            (&[0, 0, 1], "112"),
            (b"hello world", "StV1DL6CwTryKyV"),
            (&[0xff; 4], "7YXq9G"),
        ];
        for (data, string) in vectors {
            let mut buffer = [0u8; MAX_ENCODED_LEN + 1];
            assert_eq!(encode(data, &mut buffer).ok(), Some(*string));
            let mut buffer = [0u8; MAX_DATA_LEN];
            assert_eq!(decode(string, &mut buffer).ok(), Some(*data));
        }
    }

    #[test]
    fn test_check() {
        // Bitcoin address of hash160 0x00..00, version 0.
        let data = [0u8; 21];
        let string = "1111111111111111111114oLvT2";
        let mut buffer = [0u8; MAX_ENCODED_LEN + 1];
        assert_eq!(encode_check(&data, &mut buffer).ok(), Some(string));
        let mut buffer = [0u8; MAX_DATA_LEN];
        assert_eq!(decode_check(string, &mut buffer).ok(), Some(&data[..]));

        // Empty data has just the checksum.
        let mut buffer = [0u8; MAX_ENCODED_LEN + 1];
        let string = encode_check(b"", &mut buffer).ok().unwrap();
        let mut buffer = [0u8; MAX_DATA_LEN];
        assert_eq!(decode_check(string, &mut buffer).ok(), Some(&b""[..]));

        // Corrupted checksum.
        let mut buffer = [0u8; MAX_DATA_LEN];
        assert!(decode_check("1111111111111111111114oLvT3", &mut buffer).is_err());
    }

    #[test]
    fn test_limits() {
        let data = [0xffu8; MAX_DATA_LEN];
        let mut encoded = [0u8; MAX_ENCODED_LEN + 1];
        let string = encode_check(&data, &mut encoded).ok().unwrap();
        assert!(string.len() <= MAX_ENCODED_LEN);
        let mut buffer = [0u8; MAX_DATA_LEN];
        assert_eq!(decode_check(string, &mut buffer).ok(), Some(&data[..]));

        let mut encoded = [0u8; MAX_ENCODED_LEN + 1];
        assert!(encode(&[0u8; MAX_DATA_LEN + 1], &mut encoded).is_err());
        assert!(encode_check(&[0u8; MAX_DATA_LEN + 1], &mut encoded).is_err());

        // A leading '1' adds a zero byte, one more than fits.
        let mut encoded = [0u8; MAX_ENCODED_LEN + 1];
        let too_long = format!("1{}", encode(&data, &mut encoded).ok().unwrap());
        let mut buffer = [0u8; MAX_DATA_LEN];
        assert!(decode(&too_long, &mut buffer).is_err());
        assert!(decode(&"2".repeat(MAX_ENCODED_LEN + 1), &mut buffer).is_err());

        assert!(decode("1\u{0}1", &mut buffer).is_err());
        assert!(decode("0OIl", &mut buffer).is_err());
    }
}

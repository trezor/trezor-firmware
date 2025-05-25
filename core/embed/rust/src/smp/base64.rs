/// Provides Base64 encoding and decoding in a `no_std` environment.
///
/// # Errors
/// - `OutputBufferTooSmall` if the provided output buffer is too short.
/// - `InvalidLength` if the input length is not a multiple of 4 for decoding.
/// - `InvalidCharacter` if an invalid Base64 character is encountered during
///   decoding.
#[derive(Debug)]
pub enum Base64Error {
    OutputBufferTooSmall,
    InvalidLength,
    InvalidCharacter,
}

/// Base64 encoding table
static B64_TABLE: [u8; 64] = *b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

/// Table for calculating padding bytes (0, 2, 1) based on input length mod 3
static MOD_TABLE: [usize; 3] = [0, 2, 1];

/// Encodes `input` bytes into Base64, writing into `output`.
/// Returns the number of bytes written on success.
pub fn base64_encode(input: &[u8], output: &mut [u8]) -> Result<usize, Base64Error> {
    let len = input.len();
    let output_len = 4 * len.div_ceil(3);
    if output.len() < output_len {
        return Err(Base64Error::OutputBufferTooSmall);
    }

    let mut i = 0;
    let mut j = 0;
    while i < len {
        let a = input[i];
        let b = if i + 1 < len { input[i + 1] } else { 0 };
        let c = if i + 2 < len { input[i + 2] } else { 0 };
        i += 3;

        let triple = ((a as u32) << 16) | ((b as u32) << 8) | (c as u32);
        output[j] = B64_TABLE[((triple >> 18) & 0x3F) as usize];
        output[j + 1] = B64_TABLE[((triple >> 12) & 0x3F) as usize];
        output[j + 2] = B64_TABLE[((triple >> 6) & 0x3F) as usize];
        output[j + 3] = B64_TABLE[(triple & 0x3F) as usize];
        j += 4;
    }

    // Apply padding
    for pad in 0..MOD_TABLE[len % 3] {
        output[output_len - 1 - pad] = b'=';
    }

    Ok(output_len)
}

/// Maps a Base64 character to its 6-bit value.
fn base64_char_value(c: u8) -> Option<u8> {
    match c {
        b'A'..=b'Z' => Some(c - b'A'),
        b'a'..=b'z' => Some(c - b'a' + 26),
        b'0'..=b'9' => Some(c - b'0' + 52),
        b'+' => Some(62),
        b'/' => Some(63),
        _ => None,
    }
}

/// Decodes Base64 `input` bytes into raw bytes, writing into `output`.
/// Returns the number of bytes written on success.
pub fn base64_decode(input: &[u8], output: &mut [u8]) -> Result<usize, Base64Error> {
    let len = input.len();
    if len % 4 != 0 {
        return Err(Base64Error::InvalidLength);
    }

    // Count padding '=' bytes
    let mut padding = 0;
    if len >= 2 {
        if input[len - 1] == b'=' {
            padding += 1;
        }
        if input[len - 2] == b'=' {
            padding += 1;
        }
    }

    let decoded_len = (len / 4) * 3 - padding;
    if output.len() < decoded_len {
        return Err(Base64Error::OutputBufferTooSmall);
    }

    let mut i = 0;
    let mut j = 0;
    while i < len {
        let v1 = base64_char_value(input[i]).ok_or(Base64Error::InvalidCharacter)? as u32;
        let v2 = base64_char_value(input[i + 1]).ok_or(Base64Error::InvalidCharacter)? as u32;
        let v3 = if input[i + 2] == b'=' {
            0
        } else {
            base64_char_value(input[i + 2]).ok_or(Base64Error::InvalidCharacter)? as u32
        };
        let v4 = if input[i + 3] == b'=' {
            0
        } else {
            base64_char_value(input[i + 3]).ok_or(Base64Error::InvalidCharacter)? as u32
        };
        i += 4;

        let triple = (v1 << 18) | (v2 << 12) | (v3 << 6) | v4;
        output[j] = ((triple >> 16) & 0xFF) as u8;
        j += 1;
        if input[i - 2] != b'=' {
            output[j] = ((triple >> 8) & 0xFF) as u8;
            j += 1;
        }
        if input[i - 1] != b'=' {
            output[j] = (triple & 0xFF) as u8;
            j += 1;
        }
    }

    Ok(decoded_len)
}

// Testing uses std; keeps `no_std` for library code.
#[cfg(test)]
extern crate std;

#[cfg(test)]
mod tests {
    use super::*;
    use std::vec::Vec;

    #[test]
    fn test_encode_decode() {
        let tests: [(&[u8], &[u8]); 7] = [
            (b"", b""),
            (b"f", b"Zg=="),
            (b"fo", b"Zm8="),
            (b"foo", b"Zm9v"),
            (b"foob", b"Zm9vYg=="),
            (b"fooba", b"Zm9vYmE="),
            (b"foobar", b"Zm9vYmFy"),
        ];
        for &(input, expected) in &tests {
            let mut enc_buf = [0u8; 16];
            let len = base64_encode(input, &mut enc_buf).unwrap();
            assert_eq!(&enc_buf[..len], expected);

            let mut dec_buf = [0u8; 16];
            let dec_len = base64_decode(&enc_buf[..len], &mut dec_buf).unwrap();
            assert_eq!(&dec_buf[..dec_len], input);
        }
    }

    #[test]
    fn test_invalid_decode() {
        let mut buf = [0u8; 16];
        assert!(matches!(
            base64_decode(b"abc", &mut buf),
            Err(Base64Error::InvalidLength)
        ));
        assert!(matches!(
            base64_decode(b"!!!!", &mut buf),
            Err(Base64Error::InvalidCharacter)
        ));
    }
}

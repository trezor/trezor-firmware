use crate::error::value_error;

pub mod aesgcm;
pub mod cosi;
pub mod crc32;
pub mod curve25519;
pub mod ed25519;
mod ffi;
pub mod hmac;
pub mod memory;
pub mod merkle;
pub mod sha256;
pub mod sha512;

#[cfg_attr(feature = "test", derive(core::fmt::Debug))]
pub enum Error {
    // Signature verification failed
    SignatureVerificationFailed,
    // Provided value is not a valid public key / signature / etc.
    InvalidEncoding,
    // Provided parameters are not accepted (e.g., signature threshold out of bounds)
    InvalidParams,
    // State precondition check failed (possibly raised by C implementation)
    InvalidContext,
}

impl From<Error> for crate::error::Error {
    fn from(e: Error) -> Self {
        match e {
            Error::SignatureVerificationFailed => value_error!(c"Signature verification failed"),
            Error::InvalidEncoding => value_error!(c"Invalid key or signature encoding"),
            Error::InvalidParams => value_error!(c"Invalid cryptographic parameters"),
            Error::InvalidContext => value_error!(c"Invalid cryptographic context"),
        }
    }
}

/// Constant time bytestring comparison for two arrays of the same length.
pub fn consteq<const N: usize>(a: &[u8; N], b: &[u8; N]) -> bool {
    let mut diff: u8 = 0;
    for i in 0..N {
        diff |= a[i] ^ b[i];
    }
    diff == 0
}

#[cfg(test)]
mod test {
    use super::*;

    #[test]
    fn test_consteq() {
        assert!(consteq(&[], &[]));
        assert!(consteq(&[0u8; 256], &[0u8; 256]));
        assert!(consteq(&[0xffu8; 256], &[0xffu8; 256]));
        assert!(consteq(b"0123456789abcdef", b"0123456789abcdef"));

        assert!(!consteq(&[0u8; 256], &[0xffu8; 256]));
        assert!(!consteq(&[0xffu8; 256], &[0u8; 256]));
        assert!(!consteq(b"0123456789abcdef", b"123456789abcdef0"));
        assert!(!consteq(b"0000000000000000", b"0000000000000001"));
    }
}

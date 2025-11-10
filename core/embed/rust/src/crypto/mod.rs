use crate::error::value_error;

pub mod aesgcm;
pub mod cosi;
pub mod crc32;
pub mod curve25519;
pub mod ed25519;
mod ffi;
pub mod hmac;
mod memory;
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

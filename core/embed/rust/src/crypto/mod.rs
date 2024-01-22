pub mod cosi;
pub mod ed25519;
mod ffi;
pub mod merkle;
pub mod sha256;

pub enum Error {
    // Signature verification failed
    SignatureVerificationFailed,
    // Provided value is not a valid public key / signature / etc.
    InvalidEncoding,
    // Provided parameters are not accepted (e.g., signature threshold out of bounds)
    InvalidParams,
}

impl From<Error> for crate::error::Error {
    fn from(e: Error) -> Self {
        match e {
            Error::SignatureVerificationFailed => value_error!("Signature verification failed"),
            Error::InvalidEncoding => value_error!("Invalid key or signature encoding"),
            Error::InvalidParams => value_error!("Invalid cryptographic parameters"),
        }
    }
}

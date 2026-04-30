pub use micropython::error::{Error, value_error};

pub trait IntoError {
    fn into_error(self) -> Error;
}

#[cfg(feature = "crypto")]
impl IntoError for trezor_crypto::Error {
    fn into_error(self) -> Error {
        match self {
            trezor_crypto::Error::SignatureVerificationFailed => value_error!(c"Signature verification failed"),
            trezor_crypto::Error::InvalidEncoding => value_error!(c"Invalid key or signature encoding"),
            trezor_crypto::Error::InvalidParams => value_error!(c"Invalid cryptographic parameters"),
            trezor_crypto::Error::InvalidContext => value_error!(c"Invalid cryptographic context"),
        }
    }
}

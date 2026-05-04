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

#[cfg(all(feature = "micropython", feature = "storage"))]
impl From<StorageError> for Error {
    fn from(err: StorageError) -> Self {
        match err {
            StorageError::InvalidData => value_error!(c"Invalid data for storage"),
            StorageError::WriteFailed => value_error!(c"Storage write failed"),
            StorageError::ReadFailed => value_error!(c"Storage read failed"),
            StorageError::DeleteFailed => value_error!(c"Storage delete failed"),
            StorageError::CounterFailed => {
                value_error!(c"Retrieving counter value failed")
            }
        }
    }
}

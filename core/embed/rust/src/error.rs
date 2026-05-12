#[cfg(feature = "micropython")]
use micropython::error::Error;

#[cfg(feature = "storage")]
use crate::trezorhal::storage::StorageError;

#[cfg(all(feature = "micropython", feature = "storage"))]
impl From<StorageError> for Error {
    fn from(err: StorageError) -> Self {
        match err {
            StorageError::InvalidData => Error::ValueError(c"Invalid data for storage"),
            StorageError::WriteFailed => Error::ValueError(c"Storage write failed"),
            StorageError::ReadFailed => Error::ValueError(c"Storage read failed"),
            StorageError::DeleteFailed => Error::ValueError(c"Storage delete failed"),
            StorageError::CounterFailed => Error::ValueError(c"Retrieving counter value failed"),
        }
    }
}

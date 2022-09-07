use core::ptr;
use cstr_core::cstr;
use crate::error::Error;
use super::ffi;



/// Storage error type.
#[derive(Copy, Clone, Debug, PartialEq, Eq)]
pub enum StorageError {
    /// Data is too long or not appropriate for the operation.
    InvalidData,
    /// Write failed.
    WriteFailed,
    /// Read failed.
    ReadFailed,
    /// Failed to perform the get-and-increment operation on a counter.
    CounterFailed,
}

impl From<StorageError> for Error {
    fn from(err: StorageError) -> Self {
        match err {
            StorageError::InvalidData => Error::ValueError(cstr!("Invalid data for storage")),
            StorageError::WriteFailed => Error::ValueError(cstr!("Storage write failed")),
            StorageError::ReadFailed => Error::ValueError(cstr!("Storage read failed")),
            StorageError::CounterFailed => {
                Error::ValueError(cstr!("Retrieving counter value failed"))
            }
        }
    }
}
pub type StorageResult<T> = Result<T, StorageError>;


pub fn storage_init(callback: Option<unsafe extern "C" fn(u32, u32, *const u8) -> u32>) {
    unsafe {
        ffi::storage_init(callback, (&ffi::HW_ENTROPY_DATA) as _, ffi::HW_ENTROPY_LEN as _);
    }
}

pub fn storage_wipe() {
    unsafe {
        ffi::storage_wipe();
    }
}

pub fn storage_unlock(pin: &str) -> bool {
    unsafe {
        let unlocked = ffi::storage_unlock(pin.as_ptr(), pin.len(), ptr::null_mut());
        unlocked == ffi::sectrue
    }
}

pub fn storage_has_pin() -> bool {
    unsafe {
        ffi::storage_has_pin() == ffi::sectrue
    }
}

pub fn storage_get_remaining() -> u32 {
    unsafe {
        ffi::storage_get_pin_rem()
    }
}

/// Get length of value stored for `appkey`.
/// Returns an error if the value does not exist.
pub fn storage_get_length(appkey: u16) -> StorageResult<usize> {
    let mut len = 0;
    if ffi::sectrue == unsafe { ffi::storage_get(appkey, ptr::null_mut() as _, 0, &mut len) } {
        Ok(len as usize)
    } else {
        Err(StorageError::ReadFailed)
    }
}

/// Get value for `appkey` from storage.
/// The provided `data` buffer must be long enough to hold the value. If the
/// buffer is shorter than the stored value, an error is returned. Use
/// `get_length` to find the size of the value beforehand. On success, the data
/// is copied to `data`, and length of copied data is returned. Data previously
/// in the buffer beyond the copied data is not modified.
/// If `appkey` is not present in storage, or the value is private and storage
/// is locked, returns an error.
pub fn storage_get(appkey: u16, data: &mut [u8]) -> StorageResult<usize> {
    let max_len = data.len().min(u16::MAX as usize) as u16;
    let mut len = 0u16;
    if ffi::sectrue
        == unsafe { ffi::storage_get(appkey, data.as_mut_ptr() as _, max_len, &mut len) }
    {
        Ok(len as usize)
    } else {
        Err(StorageError::ReadFailed)
    }
}

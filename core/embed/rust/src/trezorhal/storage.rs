#![allow(dead_code)]

use super::ffi;
use crate::error::{value_error, Error};
use core::ptr;

use num_traits::FromPrimitive;

/// Result of PIN delay callback.
#[derive(Copy, Clone, Debug, PartialEq, Eq)]
pub enum PinCallbackResult {
    /// Continue waiting for PIN unlock.
    Continue,
    /// Abort the unlock attempt before time is up.
    Abort,
}

#[derive(Copy, Clone, Debug, PartialEq, Eq, FromPrimitive)]
pub enum PinCallbackMessage {
    None,
    VerifyingPIN,
    Processing,
    Starting,
    WrongPIN,
}

/// PIN delay callback function type.
/// The storage layer will call this function while the PIN timeout is in
/// progress. This is useful for showing UI progress bar.
/// `wait` is the total number of seconds waiting.
/// `progress` is a value between 0 and 1000, where 1000 indicates 100%.
/// `message` is a message to show to the user.
pub type PinDelayCallback =
    fn(wait: u32, progress: u32, message: PinCallbackMessage) -> PinCallbackResult;

pub type ExternalSalt = [u8; ffi::EXTERNAL_SALT_SIZE as usize];

/// Static reference to the currently set PIN callback function.
static mut PIN_UI_CALLBACK: Option<PinDelayCallback> = None;

/// C-compatible wrapper for the Rust callback.
unsafe extern "C" fn callback_wrapper(
    wait: u32,
    progress: u32,
    message: ffi::storage_ui_message_t,
) -> ffi::secbool {
    let result = unsafe {
        PIN_UI_CALLBACK
            .map(|c| {
                c(
                    wait,
                    progress,
                    PinCallbackMessage::from_u32(message).unwrap_or(PinCallbackMessage::None),
                )
            })
            .unwrap_or(PinCallbackResult::Continue)
    };
    if matches!(result, PinCallbackResult::Abort) {
        ffi::sectrue
    } else {
        ffi::secfalse
    }
}

/// Storage error type.
#[derive(Copy, Clone, Debug, PartialEq, Eq)]
pub enum StorageError {
    /// Data is too long or not appropriate for the operation.
    InvalidData,
    /// Write failed.
    WriteFailed,
    /// Read failed.
    ReadFailed,
    /// Delete failed.
    DeleteFailed,
    /// Failed to perform the get-and-increment operation on a counter.
    CounterFailed,
}

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

pub type StorageResult<T> = Result<T, StorageError>;

/// Initialize the storage layer.
/// This function must be called before any other storage function.
pub fn init() {
    unsafe {
        let mut entropy_data: [u8; ffi::HW_ENTROPY_LEN as usize] =
            [0; ffi::HW_ENTROPY_LEN as usize];
        ffi::entropy_get(entropy_data.as_mut_ptr());
        ffi::storage_init(
            Some(callback_wrapper),
            entropy_data.as_ptr(),
            entropy_data.len() as u16,
        );
    }
}

/// Set the PIN callback function.
/// See documentation for `PinDelayCallback` for more information.
pub fn set_pin_delay_callback(callback: PinDelayCallback) {
    unsafe {
        PIN_UI_CALLBACK = Some(callback);
    }
}

/// Wipe storage.
pub fn wipe() {
    unsafe { ffi::storage_wipe() }
}

/// Check if storage is unlocked.
pub fn is_unlocked() -> bool {
    ffi::sectrue == unsafe { ffi::storage_is_unlocked() }
}

/// Lock storage.
pub fn lock() {
    unsafe { ffi::storage_lock() }
}

/// Unlock storage with PIN and optional external salt.
/// Returns true if the PIN + salt combination is correct.
pub fn unlock(pin: &str, salt: Option<&ExternalSalt>) -> bool {
    let salt = salt.map(|s| s.as_ptr()).unwrap_or(ptr::null());
    ffi::sectrue == unsafe { ffi::storage_unlock(pin.as_ptr() as *const _, pin.len(), salt) }
}

/// Change PIN and/or external salt.
/// Returns true if the PIN + salt combination is correct and the change was
/// successful.
pub fn change_pin(
    old_pin: &str,
    new_pin: &str,
    old_salt: Option<&ExternalSalt>,
    new_salt: Option<&ExternalSalt>,
) -> bool {
    ffi::sectrue
        == unsafe {
            ffi::storage_change_pin(
                old_pin.as_ptr() as *const _,
                old_pin.len(),
                new_pin.as_ptr() as *const _,
                new_pin.len(),
                old_salt.map(|s| s.as_ptr()).unwrap_or(ptr::null()),
                new_salt.map(|s| s.as_ptr()).unwrap_or(ptr::null()),
            )
        }
}

/// Check if storage has PIN set.
pub fn has_pin() -> bool {
    ffi::sectrue == unsafe { ffi::storage_has_pin() }
}

/// Get remaining PIN attempts.
pub fn get_pin_remaining() -> u32 {
    unsafe { ffi::storage_get_pin_rem() }
}

pub fn ensure_not_wipe_pin(pin: &str) {
    unsafe {
        ffi::storage_ensure_not_wipe_code(pin.as_ptr(), pin.len());
    }
}

/// Check if value for `appkey` exists.
pub fn has(appkey: u16) -> bool {
    ffi::sectrue == unsafe { ffi::storage_has(appkey) }
}

/// Get length of value stored for `appkey`.
/// Returns an error if the value does not exist.
pub fn get_length(appkey: u16) -> StorageResult<usize> {
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
/// is copied to `data`, and subslice is returned. Data previously
/// in the buffer beyond the copied data is not modified.
/// If `appkey` is not present in storage, or the value is private and storage
/// is locked, returns an error.
pub fn get(appkey: u16, data: &mut [u8]) -> StorageResult<&[u8]> {
    let max_len = data.len().min(u16::MAX as usize) as u16;
    let mut len = 0u16;
    if ffi::sectrue
        == unsafe { ffi::storage_get(appkey, data.as_mut_ptr() as _, max_len, &mut len) }
    {
        Ok(&data[0..len as usize])
    } else {
        Err(StorageError::ReadFailed)
    }
}

/// Set value for `appkey` in storage.
/// The maximum length of the value is `u16::MAX`. Passing longer buffers will
/// result in an error.
/// If storage is locked and the value is not public-writable, returns an error.
pub fn set(appkey: u16, data: &[u8]) -> StorageResult<()> {
    if data.len() > u16::MAX as usize {
        Err(StorageError::InvalidData)
    } else if ffi::sectrue
        == unsafe { ffi::storage_set(appkey, data.as_ptr() as _, data.len() as u16) }
    {
        Ok(())
    } else {
        Err(StorageError::WriteFailed)
    }
}

/// Set value for monotonic counter `appkey` in storage.
pub fn set_counter(appkey: u16, counter: u32) -> StorageResult<()> {
    if ffi::sectrue == unsafe { ffi::storage_set_counter(appkey, counter) } {
        Ok(())
    } else {
        Err(StorageError::WriteFailed)
    }
}

/// Atomically get and increment the value for monotonic counter `appkey` in
/// storage.
pub fn get_next_counter(appkey: u16) -> StorageResult<u32> {
    let mut counter = 0u32;
    if ffi::sectrue == unsafe { ffi::storage_next_counter(appkey, &mut counter) } {
        Ok(counter)
    } else {
        Err(StorageError::CounterFailed)
    }
}

/// Delete value for `appkey` from storage.
/// Returns Ok if the value was successfully deleted.
/// If the storage is locked, or the value does not exist in storage, returns
/// an error.
pub fn delete(appkey: u16) -> StorageResult<()> {
    if ffi::sectrue == unsafe { ffi::storage_delete(appkey) } {
        Ok(())
    } else {
        Err(StorageError::DeleteFailed)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const APPKEY: u16 = 0x0101;

    fn init_storage(unlock: bool) {
        unsafe {
            ffi::flash_init();
        }
        init();
        wipe();
        lock();
        if unlock {
            super::unlock("", None);
        }
    }

    #[test]
    fn test_init() {
        init();
    }

    static mut PIN_CALLBACK_CALLED: bool = false;

    fn pin_callback(_wait: u32, _progress: u32, _message: PinCallbackMessage) -> PinCallbackResult {
        unsafe {
            PIN_CALLBACK_CALLED = true;
        }
        PinCallbackResult::Continue
    }

    #[test]
    fn test_callback() {
        set_pin_delay_callback(pin_callback);
        init_storage(false);
        unsafe {
            PIN_CALLBACK_CALLED = false;
        }
        unlock("", None);
        assert!(unsafe { PIN_CALLBACK_CALLED });
    }

    #[test]
    fn test_get_set() {
        init_storage(true);
        let mut data = [0u8; 42];
        for i in 0..data.len() {
            data[i] = i as u8;
        }
        assert!(set(APPKEY, &data).is_ok());
        let mut data2 = [0u8; 42];
        assert_eq!(get(APPKEY, &mut data2).unwrap().len(), data.len());
        assert_eq!(get(APPKEY, &mut data2).unwrap(), data);
        assert_eq!(data, data2);
    }

    #[test]
    fn test_unlock() {
        init_storage(false);
        assert!(!is_unlocked());
        let buf = [0u8; 32];
        assert_eq!(set(APPKEY, &buf), Err(StorageError::WriteFailed));
        assert!(unlock("", None));
        assert!(is_unlocked());
        assert_eq!(set(APPKEY, &buf), Ok(()));
    }

    #[test]
    fn test_pin() {
        init_storage(false);
        assert!(!is_unlocked());
        assert!(!has_pin());
        assert!(unlock("", None));
        assert!(is_unlocked());
        assert!(!has_pin());

        lock();
        assert!(!is_unlocked());
        assert!(!has_pin());

        assert!(!unlock("1234", None));

        //unlock("", None);
        assert!(change_pin("", "1234", None, None));
        assert!(has_pin());

        lock();
        assert!(!unlock("", None));
        assert!(unlock("1234", None));
    }
}

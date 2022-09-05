use core::ptr;
use super::ffi;



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

pub fn storage_get_remaining() -> u32 {
    unsafe {
        ffi::storage_get_pin_rem()
    }
}

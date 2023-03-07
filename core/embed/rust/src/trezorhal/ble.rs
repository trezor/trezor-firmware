use super::ffi;

pub fn ble_connected() -> bool {
    unsafe { ffi::ble_connected() }
}

use super::ffi;

pub fn ble_connected() -> bool {
    unsafe { ffi::ble_connected() }
}

pub fn start_advertising(whitelist: bool) {
    unsafe { ffi::start_advertising(whitelist) }
}

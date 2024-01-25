use super::ffi;

pub fn screenshot() -> bool {
    unsafe { ffi::screenshot() }
}

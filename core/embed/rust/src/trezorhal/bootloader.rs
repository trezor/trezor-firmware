use super::ffi;

pub fn debuglink_process() {
    unsafe { ffi::debuglink_process() }
}

pub fn debuglink_notify_layout_change() {
    unsafe { ffi::debuglink_notify_layout_change() }
}

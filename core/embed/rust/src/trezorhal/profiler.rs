use super::ffi;

pub fn start() {
    unsafe {
        ffi::profiler_start();
    }
}
pub fn end() {
    unsafe {
        ffi::profiler_end();
    }
}
pub fn init() {
    unsafe {
        ffi::profiler_init();
    }
}

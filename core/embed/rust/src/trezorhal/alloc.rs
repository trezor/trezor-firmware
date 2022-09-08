use core::slice;
use super::ffi;

pub fn alloc_only(size: usize) -> &'static mut [u8] {
    unsafe {
        let data= slice::from_raw_parts_mut(ffi::alloc_only(size as _) as _, size);
        data
    }
}

pub fn alloc_only_init(clear: bool) {
    unsafe {
        ffi::alloc_only_init(clear);
    }
}

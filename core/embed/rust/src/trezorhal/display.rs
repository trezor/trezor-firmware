use super::ffi;

#[cfg(feature = "framebuffer")]
use core::ptr;

use ffi::{DISPLAY_RESX_, DISPLAY_RESY_};

pub const DISPLAY_RESX: u32 = DISPLAY_RESX_;
pub const DISPLAY_RESY: u32 = DISPLAY_RESY_;

pub fn backlight(val: i32) -> i32 {
    unsafe { ffi::display_set_backlight(val) }
}

pub fn sync() {
    // NOTE: The sync operation is not called for tests because the linker
    // would otherwise report missing symbols if the tests are built with ASAN.
    #[cfg(not(any(feature = "framebuffer", feature = "test")))]
    unsafe {
        ffi::display_wait_for_sync();
    }
}

pub fn refresh() {
    unsafe {
        ffi::display_refresh();
    }
}

#[cfg(feature = "framebuffer")]
pub fn get_frame_buffer() -> Option<(&'static mut [u8], usize)> {
    let mut fb_info = ffi::display_fb_info_t {
        ptr: ptr::null_mut(),
        size: 0,
        stride: 0,
    };

    unsafe { ffi::display_get_frame_buffer(&mut fb_info) };

    if fb_info.ptr.is_null() {
        return None;
    }

    let fb = unsafe { core::slice::from_raw_parts_mut(fb_info.ptr as *mut u8, fb_info.size) };

    Some((fb, fb_info.stride))
}

use super::ffi;

#[cfg(feature = "framebuffer")]
use core::ptr;

pub use ffi::{DISPLAY_RESX, DISPLAY_RESY};

pub type FontInfo = ffi::font_info_t;

pub fn backlight(val: i32) -> i32 {
    unsafe { ffi::display_set_backlight(val) }
}

pub fn get_font_info(font: i32) -> Option<FontInfo> {
    unsafe {
        let font = ffi::get_font_info(font);
        Some(*font.as_ref()?)
    }
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
pub fn get_frame_buffer() -> (&'static mut [u8], usize) {
    let mut fb_info = ffi::display_fb_info_t {
        ptr: ptr::null_mut(),
        stride: 0,
    };

    unsafe { ffi::display_get_frame_buffer(&mut fb_info) };

    let fb = unsafe {
        core::slice::from_raw_parts_mut(
            fb_info.ptr as *mut u8,
            DISPLAY_RESY as usize * fb_info.stride,
        )
    };

    (fb, fb_info.stride)
}

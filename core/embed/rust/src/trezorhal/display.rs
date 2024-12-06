use super::ffi;

#[cfg(feature = "framebuffer")]
use core::ptr;

pub use ffi::{DISPLAY_RESX, DISPLAY_RESY};

pub type FontInfo = ffi::font_info_t;

pub fn backlight(val: i32) -> i32 {
    unsafe { ffi::display_set_backlight(val) }
}

pub fn get_font_info(font: i32) -> Option<FontInfo> {
    // SAFETY:
    // - `ffi::get_font_info` returns either null (for invalid fonts) or a pointer
    //   to a static font_info_t struct
    // - The font_info_t data is in ROM, making it immutable and static
    // - The font_info_t contains pointers to static glyph data arrays also in ROM
    // - All font data is generated at compile time and included in the binary
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
pub fn get_frame_buffer() -> Option<(&'static mut [u8], usize)> {
    let mut fb_info = ffi::display_fb_info_t {
        ptr: ptr::null_mut(),
        stride: 0,
    };

    unsafe { ffi::display_get_frame_buffer(&mut fb_info) };

    if fb_info.ptr.is_null() {
        return None;
    }

    let fb = unsafe {
        core::slice::from_raw_parts_mut(
            fb_info.ptr as *mut u8,
            DISPLAY_RESY as usize * fb_info.stride,
        )
    };

    Some((fb, fb_info.stride))
}

use super::ffi;

#[cfg(feature = "framebuffer")]
use core::ptr;

pub use ffi::{DISPLAY_RESX, DISPLAY_RESY};

pub fn backlight(val: i32) -> i32 {
    unsafe { ffi::display_set_backlight(val) }
}

pub fn text_width(text: &str, font: i32) -> i16 {
    unsafe {
        ffi::font_text_width(font, text.as_ptr() as _, text.len() as _)
            .try_into()
            .unwrap_or(i16::MAX)
    }
}

pub fn char_width(ch: char, font: i32) -> i16 {
    let mut buf = [0u8; 4];
    let encoding = ch.encode_utf8(&mut buf);
    text_width(encoding, font)
}

pub fn get_char_glyph(ch: u16, font: i32) -> *const u8 {
    unsafe { ffi::font_get_glyph(font, ch) }
}

pub fn text_height(font: i32) -> i16 {
    unsafe { ffi::font_height(font).try_into().unwrap_or(i16::MAX) }
}

pub fn text_max_height(font: i32) -> i16 {
    unsafe { ffi::font_max_height(font).try_into().unwrap_or(i16::MAX) }
}

pub fn text_baseline(font: i32) -> i16 {
    unsafe { ffi::font_baseline(font).try_into().unwrap_or(i16::MAX) }
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

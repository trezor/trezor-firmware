use super::ffi;
use core::{ops::DerefMut, ptr};
use cty::c_int;

use crate::trezorhal::buffers::BufferText;

pub use ffi::{DISPLAY_RESX, DISPLAY_RESY};

#[cfg(feature = "framebuffer")]
pub use ffi::{
    DISPLAY_FRAMEBUFFER_HEIGHT, DISPLAY_FRAMEBUFFER_OFFSET_X, DISPLAY_FRAMEBUFFER_OFFSET_Y,
    DISPLAY_FRAMEBUFFER_WIDTH,
};

#[cfg(all(feature = "framebuffer", not(feature = "framebuffer32bit")))]
#[derive(Copy, Clone)]
pub struct FrameBuffer(*mut u16);

#[cfg(all(feature = "framebuffer", feature = "framebuffer32bit"))]
#[derive(Copy, Clone)]
pub struct FrameBuffer(*mut u32);

#[derive(PartialEq, Debug, Eq, FromPrimitive, Clone, Copy)]
pub enum ToifFormat {
    FullColorBE = ffi::toif_format_t_TOIF_FULL_COLOR_BE as _,
    GrayScaleOH = ffi::toif_format_t_TOIF_GRAYSCALE_OH as _,
    FullColorLE = ffi::toif_format_t_TOIF_FULL_COLOR_LE as _,
    GrayScaleEH = ffi::toif_format_t_TOIF_GRAYSCALE_EH as _,
}

pub fn backlight(val: i32) -> i32 {
    unsafe { ffi::display_backlight(val) }
}

pub fn text(baseline_x: i16, baseline_y: i16, text: &str, font: i32, fgcolor: u16, bgcolor: u16) {
    unsafe {
        ffi::display_text(
            baseline_x.into(),
            baseline_y.into(),
            text.as_ptr() as _,
            text.len() as _,
            font,
            fgcolor,
            bgcolor,
        )
    }
}

pub fn text_into_buffer(text: &str, font: i32, buffer: &mut BufferText, x_offset: i16) {
    unsafe {
        ffi::display_text_render_buffer(
            text.as_ptr() as _,
            text.len() as _,
            font,
            buffer.deref_mut(),
            x_offset.into(),
        )
    }
}

pub fn text_width(text: &str, font: i32) -> i16 {
    unsafe {
        ffi::display_text_width(text.as_ptr() as _, text.len() as _, font)
            .try_into()
            .unwrap_or(i16::MAX)
    }
}

pub fn char_width(ch: char, font: i32) -> i16 {
    let mut buf = [0u8; 4];
    let encoding = ch.encode_utf8(&mut buf);
    text_width(encoding, font)
}

pub fn get_char_glyph(ch: u8, font: i32) -> *const u8 {
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

#[inline(always)]
#[cfg(all(feature = "disp_i8080_16bit_dw", not(feature = "disp_i8080_8bit_dw")))]
pub fn pixeldata(c: u16) {
    unsafe {
        ffi::DISPLAY_DATA_ADDRESS.write_volatile(c);
    }
}

#[cfg(feature = "framebuffer")]
pub fn get_fb_addr() -> FrameBuffer {
    unsafe { FrameBuffer(ffi::display_get_fb_addr() as _) }
}

#[inline(always)]
#[cfg(feature = "disp_i8080_8bit_dw")]
pub fn pixeldata(c: u16) {
    unsafe {
        ffi::DISPLAY_DATA_ADDRESS.write_volatile((c & 0xff) as u8);
        ffi::DISPLAY_DATA_ADDRESS.write_volatile((c >> 8) as u8);
    }
}

#[inline(always)]
#[cfg(all(feature = "framebuffer", not(feature = "framebuffer32bit")))]
pub fn pixel(fb: FrameBuffer, x: i16, y: i16, c: u16) {
    unsafe {
        let addr = fb.0.offset(
            ((y as u32 + DISPLAY_FRAMEBUFFER_OFFSET_Y) * DISPLAY_FRAMEBUFFER_WIDTH
                + (x as u32 + DISPLAY_FRAMEBUFFER_OFFSET_X)) as isize,
        );
        addr.write_volatile(c);
    }
}

#[inline(always)]
#[cfg(all(feature = "framebuffer", feature = "framebuffer32bit"))]
pub fn pixel(fb: FrameBuffer, x: i16, y: i16, c: u32) {
    unsafe {
        let addr = fb.0.offset(
            ((y as u32 + DISPLAY_FRAMEBUFFER_OFFSET_Y) * DISPLAY_FRAMEBUFFER_WIDTH
                + (x as u32 + DISPLAY_FRAMEBUFFER_OFFSET_X)) as isize,
        );
        addr.write_volatile(c);
    }
}

#[inline(always)]
#[cfg(not(any(feature = "disp_i8080_16bit_dw", feature = "disp_i8080_8bit_dw")))]
pub fn pixeldata(c: u16) {
    unsafe {
        ffi::display_pixeldata(c);
    }
}

pub fn pixeldata_dirty() {
    unsafe {
        ffi::display_pixeldata_dirty();
    }
}

pub fn set_window(x0: u16, y0: u16, x1: u16, y1: u16) {
    unsafe {
        ffi::display_set_window(x0, y0, x1, y1);
    }
}

pub fn get_offset() -> (i16, i16) {
    unsafe {
        let mut x: c_int = 0;
        let mut y: c_int = 0;
        ffi::display_offset(ptr::null_mut(), &mut x, &mut y);
        (x as i16, y as i16)
    }
}

pub fn sync() {
    unsafe {
        ffi::display_sync();
    }
}

pub fn refresh() {
    unsafe {
        ffi::display_refresh();
    }
}

pub fn clear() {
    unsafe {
        ffi::display_clear();
    }
}

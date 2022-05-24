use super::ffi;
use core::ptr;

pub struct ToifInfo {
    pub width: u16,
    pub height: u16,
    pub grayscale: bool,
}

pub fn backlight(val: i32) -> i32 {
    unsafe { ffi::display_backlight(val) }
}

pub fn text(baseline_x: i32, baseline_y: i32, text: &str, font: i32, fgcolor: u16, bgcolor: u16) {
    unsafe {
        ffi::display_text(
            baseline_x,
            baseline_y,
            text.as_ptr() as _,
            text.len() as _,
            font,
            fgcolor,
            bgcolor,
        )
    }
}

pub fn text_width(text: &str, font: i32) -> i32 {
    unsafe { ffi::display_text_width(text.as_ptr() as _, text.len() as _, font) }
}

pub fn char_width(ch: char, font: i32) -> i32 {
    let mut buf = [0u8; 4];
    let encoding = ch.encode_utf8(&mut buf);
    text_width(encoding, font)
}

pub fn text_height(font: i32) -> i32 {
    unsafe { ffi::display_text_height(font) }
}

pub fn bar(x: i32, y: i32, w: i32, h: i32, fgcolor: u16) {
    unsafe { ffi::display_bar(x, y, w, h, fgcolor) }
}

pub fn bar_radius(x: i32, y: i32, w: i32, h: i32, fgcolor: u16, bgcolor: u16, radius: u8) {
    unsafe { ffi::display_bar_radius(x, y, w, h, fgcolor, bgcolor, radius) }
}

pub fn icon(x: i32, y: i32, w: i32, h: i32, data: &[u8], fgcolor: u16, bgcolor: u16) {
    unsafe {
        ffi::display_icon(
            x,
            y,
            w,
            h,
            data.as_ptr() as _,
            data.len() as _,
            fgcolor,
            bgcolor,
        )
    }
}

pub fn image(x: i32, y: i32, w: i32, h: i32, data: &[u8]) {
    unsafe { ffi::display_image(x, y, w, h, data.as_ptr() as _, data.len() as _) }
}

pub fn toif_info(data: &[u8]) -> Result<ToifInfo, ()> {
    let mut width: cty::uint16_t = 0;
    let mut height: cty::uint16_t = 0;
    let mut grayscale: bool = false;
    if unsafe {
        ffi::display_toif_info(
            data.as_ptr() as _,
            data.len() as _,
            &mut width,
            &mut height,
            &mut grayscale,
        )
    } {
        Ok(ToifInfo {
            width,
            height,
            grayscale,
        })
    } else {
        Err(())
    }
}

pub fn loader(
    progress: u16,
    indeterminate: bool,
    yoffset: i32,
    fgcolor: u16,
    bgcolor: u16,
    icon: Option<&[u8]>,
    iconfgcolor: u16,
) {
    unsafe {
        ffi::display_loader(
            progress,
            indeterminate,
            yoffset,
            fgcolor,
            bgcolor,
            icon.map(|i| i.as_ptr()).unwrap_or(ptr::null()),
            icon.map(|i| i.len()).unwrap_or(0) as _,
            iconfgcolor,
        );
    }
}

#[inline(always)]
#[cfg(all(feature = "model_tt", target_arch = "arm"))]
pub fn pixeldata(c: u16) {
    unsafe {
        ffi::DISPLAY_DATA_ADDRESS.write_volatile((c >> 8) as u8);
        ffi::DISPLAY_DATA_ADDRESS.write_volatile((c & 0xff) as u8);
    }
}

#[inline(always)]
#[cfg(not(all(feature = "model_tt", target_arch = "arm")))]
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

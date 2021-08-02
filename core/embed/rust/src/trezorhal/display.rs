extern "C" {
    // trezorhal/display.c
    fn display_backlight(val: cty::c_int) -> cty::c_int;
    fn display_text(
        x: cty::c_int,
        y: cty::c_int,
        text: *const cty::c_char,
        textlen: cty::c_int,
        font: cty::c_int,
        fgcolor: cty::uint16_t,
        bgcolor: cty::uint16_t,
    );
    fn display_text_width(
        text: *const cty::c_char,
        textlen: cty::c_int,
        font: cty::c_int,
    ) -> cty::c_int;
    fn display_bar(x: cty::c_int, y: cty::c_int, w: cty::c_int, h: cty::c_int, c: cty::uint16_t);
    fn display_bar_radius(
        x: cty::c_int,
        y: cty::c_int,
        w: cty::c_int,
        h: cty::c_int,
        c: cty::uint16_t,
        b: cty::uint16_t,
        r: cty::uint8_t,
    );
    fn display_icon(
        x: cty::c_int,
        y: cty::c_int,
        w: cty::c_int,
        h: cty::c_int,
        data: *const cty::c_void,
        len: cty::uint32_t,
        fgcolor: cty::uint16_t,
        bgcolor: cty::uint16_t,
    );
    fn display_toif_info(
        data: *const cty::uint8_t,
        len: cty::uint32_t,
        out_w: *mut cty::uint16_t,
        out_h: *mut cty::uint16_t,
        out_grayscale: *mut bool,
    ) -> bool;
}

use crate::ui::component::model::constants::{HEIGHT, WIDTH};

pub struct ToifInfo {
    pub width: u16,
    pub height: u16,
    pub grayscale: bool,
}

pub fn width() -> i32 {
    WIDTH
}

pub fn height() -> i32 {
    HEIGHT
}

pub fn backlight(val: i32) -> i32 {
    unsafe { display_backlight(val) }
}

pub fn text(baseline_x: i32, baseline_y: i32, text: &[u8], font: i32, fgcolor: u16, bgcolor: u16) {
    unsafe {
        display_text(
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

pub fn text_width(text: &[u8], font: i32) -> i32 {
    unsafe { display_text_width(text.as_ptr() as _, text.len() as _, font) }
}

pub fn bar(x: i32, y: i32, w: i32, h: i32, fgcolor: u16) {
    unsafe { display_bar(x, y, w, h, fgcolor) }
}

pub fn bar_radius(x: i32, y: i32, w: i32, h: i32, fgcolor: u16, bgcolor: u16, radius: u8) {
    unsafe { display_bar_radius(x, y, w, h, fgcolor, bgcolor, radius) }
}

pub fn icon(x: i32, y: i32, w: i32, h: i32, data: &[u8], fgcolor: u16, bgcolor: u16) {
    unsafe {
        display_icon(
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

pub fn toif_info(data: &[u8]) -> Result<ToifInfo, ()> {
    let mut width: cty::uint16_t = 0;
    let mut height: cty::uint16_t = 0;
    let mut grayscale: bool = false;
    if unsafe {
        display_toif_info(
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

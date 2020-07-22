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
}

const WIDTH: u16 = 240;
const HEIGHT: u16 = 240;

pub fn width() -> u16 {
    WIDTH
}

pub fn height() -> u16 {
    HEIGHT
}

pub fn backlight(val: i32) -> i32 {
    unsafe { display_backlight(val) }
}

pub fn text(x: i32, y: i32, text: &[u8], font: i32, fgcolor: u16, bgcolor: u16) {
    unsafe {
        display_text(
            x,
            y,
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

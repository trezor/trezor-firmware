use crate::trezorhal::display;

use super::math::{Offset, Point, Rect};

pub fn width() -> i32 {
    display::width()
}

pub fn height() -> i32 {
    display::height()
}

pub fn size() -> Offset {
    Offset::new(width(), height())
}

pub fn backlight(val: i32) -> i32 {
    display::backlight(val)
}

pub fn rect(r: Rect, fg_color: u16) {
    display::bar(r.x0, r.y0, r.width(), r.height(), fg_color);
}

pub fn rounded_rect(r: Rect, fg_color: u16, bg_color: u16, radius: u8) {
    display::bar_radius(
        r.x0,
        r.y0,
        r.width(),
        r.height(),
        fg_color,
        bg_color,
        radius,
    );
}

pub fn text(baseline: Point, text: &[u8], font: i32, fg_color: u16, bg_color: u16) {
    display::text(baseline.x, baseline.y, text, font, fg_color, bg_color)
}

pub fn text_width(text: &[u8], font: i32) -> i32 {
    display::text_width(text, font)
}

pub fn line_height() -> i32 {
    display::line_height()
}

use crate::trezorhal::display;

use super::math::{Color, Offset, Point, Rect};

pub fn width() -> i32 {
    display::width()
}

pub fn height() -> i32 {
    display::height()
}

pub fn size() -> Offset {
    Offset::new(width(), height())
}

pub fn screen() -> Rect {
    Rect::with_size(Point::zero(), size())
}

pub fn backlight(val: i32) -> i32 {
    display::backlight(val)
}

pub fn rect(r: Rect, fg_color: Color) {
    display::bar(r.x0, r.y0, r.width(), r.height(), fg_color.into());
}

pub fn rounded_rect(r: Rect, fg_color: Color, bg_color: Color, radius: u8) {
    display::bar_radius(
        r.x0,
        r.y0,
        r.width(),
        r.height(),
        fg_color.into(),
        bg_color.into(),
        radius,
    );
}

pub fn text(baseline: Point, text: &[u8], font: i32, fg_color: Color, bg_color: Color) {
    display::text(
        baseline.x,
        baseline.y,
        text,
        font,
        fg_color.into(),
        bg_color.into(),
    )
}

pub fn text_width(text: &[u8], font: i32) -> i32 {
    display::text_width(text, font)
}

pub fn text_height() -> i32 {
    const TEXT_HEIGHT: i32 = 16;
    TEXT_HEIGHT
}

pub fn line_height() -> i32 {
    const LINE_HEIGHT: i32 = 26;
    LINE_HEIGHT
}

use crate::trezorhal::display;

use super::{
    component::model::constants,
    geometry::{Offset, Point, Rect},
};

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
    Rect::from_top_left_and_size(Point::zero(), size())
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

pub fn icon(center: Point, data: &[u8], fg_color: Color, bg_color: Color) {
    let toif_info = display::toif_info(data).unwrap();
    assert!(toif_info.grayscale);

    let r = Rect::from_center_and_size(
        center,
        Offset::new(toif_info.width as _, toif_info.height as _),
    );
    display::icon(
        r.x0,
        r.y0,
        r.width(),
        r.height(),
        &data[12..], // skip TOIF header
        fg_color.into(),
        bg_color.into(),
    );
}

pub fn text(baseline: Point, text: &[u8], font: Font, fg_color: Color, bg_color: Color) {
    display::text(
        baseline.x,
        baseline.y,
        text,
        font.0,
        fg_color.into(),
        bg_color.into(),
    );
}

pub fn text_width(text: &[u8], font: Font) -> i32 {
    display::text_width(text, font.0)
}

pub fn text_height() -> i32 {
    constants::TEXT_HEIGHT
}

pub fn line_height() -> i32 {
    constants::LINE_HEIGHT
}

#[derive(Copy, Clone, PartialEq, Eq)]
pub struct Font(i32);

impl Font {
    pub const fn new(id: i32) -> Self {
        Self(id)
    }

    pub fn text_width(self, text: &[u8]) -> i32 {
        text_width(text, self)
    }

    pub fn line_height(self) -> i32 {
        line_height()
    }
}

#[derive(Copy, Clone, PartialEq, Eq)]
pub struct Color(u16);

impl Color {
    pub const fn from_u16(val: u16) -> Self {
        Self(val)
    }

    pub const fn rgb(r: u8, g: u8, b: u8) -> Self {
        let r = (r as u16 & 0xF8) << 8;
        let g = (g as u16 & 0xFC) << 3;
        let b = (b as u16 & 0xF8) >> 3;
        Self(r | g | b)
    }

    pub const fn r(self) -> u8 {
        (self.0 >> 8) as u8 & 0xF8
    }

    pub const fn g(self) -> u8 {
        (self.0 >> 3) as u8 & 0xFC
    }

    pub const fn b(self) -> u8 {
        (self.0 << 3) as u8 & 0xF8
    }

    pub fn blend(self, other: Self, t: f32) -> Self {
        Self::rgb(
            lerp(self.r(), other.r(), t),
            lerp(self.g(), other.g(), t),
            lerp(self.b(), other.b(), t),
        )
    }

    pub fn to_u16(self) -> u16 {
        self.0
    }
}

impl From<u16> for Color {
    fn from(val: u16) -> Self {
        Self(val)
    }
}

impl From<Color> for u16 {
    fn from(val: Color) -> Self {
        val.to_u16()
    }
}

fn lerp(a: u8, b: u8, t: f32) -> u8 {
    (a as f32 + t * (b - a) as f32) as u8
}

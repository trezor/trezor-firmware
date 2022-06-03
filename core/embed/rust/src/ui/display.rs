use super::constant;
use crate::{
    time::Duration,
    trezorhal::{display, time},
};
use core::cmp::{max, min};

use super::geometry::{Offset, Point, Rect};

pub fn clamp_coords(pos: Point, size: Offset) -> Rect {
    let x0 = max(pos.x, 0);
    let y0 = max(pos.y, 0);
    let x1 = min(pos.x + size.x, constant::WIDTH);
    let y1 = min(pos.y + size.y, constant::HEIGHT);

    Rect::new(Point::new(x0, y0), Point::new(x1, y1))
}

pub fn backlight() -> i32 {
    display::backlight(-1)
}

pub fn set_backlight(val: i32) {
    display::backlight(val);
}

pub fn fade_backlight(target: i32) {
    const BACKLIGHT_DELAY: Duration = Duration::from_millis(14);
    const BACKLIGHT_STEP: usize = 15;

    let current = backlight();
    if current < target {
        for val in (current..target).step_by(BACKLIGHT_STEP) {
            set_backlight(val);
            time::sleep(BACKLIGHT_DELAY);
        }
    } else {
        for val in (target..current).rev().step_by(BACKLIGHT_STEP) {
            set_backlight(val);
            time::sleep(BACKLIGHT_DELAY);
        }
    }
}

pub fn rect_fill(r: Rect, fg_color: Color) {
    display::bar(r.x0, r.y0, r.width(), r.height(), fg_color.into());
}

pub fn rect_stroke(r: Rect, fg_color: Color) {
    display::bar(r.x0, r.y0, r.width(), 1, fg_color.into());
    display::bar(r.x0, r.y0 + r.height() - 1, r.width(), 1, fg_color.into());
    display::bar(r.x0, r.y0, 1, r.height(), fg_color.into());
    display::bar(r.x0 + r.width() - 1, r.y0, 1, r.height(), fg_color.into());
}

pub fn rect_fill_rounded(r: Rect, fg_color: Color, bg_color: Color, radius: u8) {
    assert!([2, 4, 8, 16].iter().any(|allowed| radius == *allowed));
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

/// NOTE: Cannot start at odd x-coordinate. In this case icon is shifted 1px
/// left.
pub fn icon_top_left(top_left: Point, data: &[u8], fg_color: Color, bg_color: Color) {
    let toif_info = display::toif_info(data).unwrap();
    assert!(toif_info.grayscale);
    display::icon(
        top_left.x,
        top_left.y,
        toif_info.width.into(),
        toif_info.height.into(),
        &data[12..], // Skip TOIF header.
        fg_color.into(),
        bg_color.into(),
    );
}

pub fn icon(center: Point, data: &[u8], fg_color: Color, bg_color: Color) {
    let toif_info = display::toif_info(data).unwrap();
    assert!(toif_info.grayscale);

    let r = Rect::from_center_and_size(
        center,
        Offset::new(toif_info.width.into(), toif_info.height.into()),
    );
    display::icon(
        r.x0,
        r.y0,
        r.width(),
        r.height(),
        &data[12..], // Skip TOIF header.
        fg_color.into(),
        bg_color.into(),
    );
}

// Used on T1 only.
pub fn rect_fill_rounded1(r: Rect, fg_color: Color, bg_color: Color) {
    display::bar(r.x0, r.y0, r.width(), r.height(), fg_color.into());
    let corners = [
        r.top_left(),
        r.top_right() - Offset::x(1),
        r.bottom_right() - Offset::uniform(1),
        r.bottom_left() - Offset::y(1),
    ];
    for p in corners.iter() {
        display::bar(p.x, p.y, 1, 1, bg_color.into());
    }
}

// Used on T1 only.
pub fn dotted_line(start: Point, width: i32, color: Color) {
    for x in (start.x..width).step_by(2) {
        display::bar(x, start.y, 1, 1, color.into());
    }
}

pub const LOADER_MIN: u16 = 0;
pub const LOADER_MAX: u16 = 1000;

pub fn loader(
    progress: u16,
    y_offset: i32,
    fg_color: Color,
    bg_color: Color,
    icon: Option<(&[u8], Color)>,
) {
    display::loader(
        progress,
        false,
        y_offset,
        fg_color.into(),
        bg_color.into(),
        icon.map(|i| i.0),
        icon.map(|i| i.1.into()).unwrap_or(0),
    );
}

pub fn loader_indeterminate(
    progress: u16,
    y_offset: i32,
    fg_color: Color,
    bg_color: Color,
    icon: Option<(&[u8], Color)>,
) {
    display::loader(
        progress,
        true,
        y_offset,
        fg_color.into(),
        bg_color.into(),
        icon.map(|i| i.0),
        icon.map(|i| i.1.into()).unwrap_or(0),
    );
}

pub fn text(baseline: Point, text: &str, font: Font, fg_color: Color, bg_color: Color) {
    display::text(
        baseline.x,
        baseline.y,
        text,
        font.0,
        fg_color.into(),
        bg_color.into(),
    );
}

pub fn text_center(baseline: Point, text: &str, font: Font, fg_color: Color, bg_color: Color) {
    let w = font.text_width(text);
    display::text(
        baseline.x - w / 2,
        baseline.y,
        text,
        font.0,
        fg_color.into(),
        bg_color.into(),
    );
}

pub fn text_right(baseline: Point, text: &str, font: Font, fg_color: Color, bg_color: Color) {
    let w = font.text_width(text);
    display::text(
        baseline.x - w,
        baseline.y,
        text,
        font.0,
        fg_color.into(),
        bg_color.into(),
    );
}

#[inline(always)]
pub fn pixeldata(color: Color) {
    display::pixeldata(color.into());
}

pub fn pixeldata_dirty() {
    display::pixeldata_dirty();
}

pub fn set_window(window: Rect) {
    display::set_window(
        window.x0 as u16,
        window.y0 as u16,
        window.x1 as u16 - 1,
        window.y1 as u16 - 1,
    );
}

pub fn interpolate_colors(color0: Color, color1: Color, step: u16) -> Color {
    let cr: u16 = ((color0.r() as u16) * step + (color1.r() as u16) * (15 - step)) / 15;
    let cg: u16 = ((color0.g() as u16) * step + (color1.g() as u16) * (15 - step)) / 15;
    let cb: u16 = ((color0.b() as u16) * step + (color1.b() as u16) * (15 - step)) / 15;
    Color::rgb(cr as u8, cg as u8, cb as u8)
}

pub fn get_color_table(fg_color: Color, bg_color: Color) -> [Color; 16] {
    let mut table: [Color; 16] = [Color::from_u16(0); 16];

    for (i, item) in table.iter_mut().enumerate() {
        *item = interpolate_colors(fg_color, bg_color, i as u16);
    }

    table
}

pub struct Glyph {
    width: i32,
    height: i32,
    adv: i32,
    bearing_x: i32,
    bearing_y: i32,
    data: *const u8,
}

impl Glyph {
    pub fn new(
        width: i32,
        height: i32,
        adv: i32,
        bearing_x: i32,
        bearing_y: i32,
        data: *const u8,
    ) -> Self {
        Glyph {
            width,
            height,
            adv,
            bearing_x,
            bearing_y,
            data,
        }
    }

    pub fn print(&self, pos: Point, colortable: [Color; 16]) -> i32 {
        let bearing = Offset::new(self.bearing_x as i32, -(self.bearing_y as i32));
        let size = Offset::new((self.width) as i32, (self.height) as i32);
        let pos_adj = pos + bearing;
        let window = clamp_coords(pos_adj, size);

        set_window(window);

        for i in window.y0..window.y1 {
            for j in window.x0..window.x1 {
                let rx = j - pos_adj.x;
                let ry = i - pos_adj.y;

                let c = self.get_pixel_data(rx, ry);
                pixeldata(colortable[c as usize]);
            }
        }
        self.adv
    }

    pub fn unpack_bpp1(&self, a: i32) -> u8 {
        unsafe {
            let c_data = self.data.offset((a / 8) as isize);
            ((*c_data >> (7 - (a % 8))) & 0x01) * 15
        }
    }

    pub fn unpack_bpp2(&self, a: i32) -> u8 {
        unsafe {
            let c_data = self.data.offset((a / 4) as isize);
            ((*c_data >> (6 - (a % 4) * 2)) & 0x03) * 5
        }
    }

    pub fn unpack_bpp4(&self, a: i32) -> u8 {
        unsafe {
            let c_data = self.data.offset((a / 2) as isize);
            (*c_data >> (4 - (a % 2) * 4)) & 0x0F
        }
    }

    pub fn unpack_bpp8(&self, a: i32) -> u8 {
        unsafe {
            let c_data = self.data.offset((a) as isize);
            *c_data >> 4
        }
    }

    pub fn get_advance(&self) -> i32 {
        self.adv
    }
    pub fn get_width(&self) -> i32 {
        self.width
    }
    pub fn get_height(&self) -> i32 {
        self.height
    }
    pub fn get_bearing_x(&self) -> i32 {
        self.bearing_x
    }
    pub fn get_bearing_y(&self) -> i32 {
        self.bearing_y
    }

    pub fn get_pixel_data(&self, x: i32, y: i32) -> u8 {
        let a = x + y * self.width;

        match constant::FONT_BPP {
            1 => self.unpack_bpp1(a),
            2 => self.unpack_bpp2(a),
            4 => self.unpack_bpp4(a),
            8 => self.unpack_bpp8(a),
            _ => 0,
        }
    }
}

#[derive(Copy, Clone, PartialEq, Eq)]
pub struct Font(i32);

impl Font {
    pub const fn new(id: i32) -> Self {
        Self(id)
    }

    pub fn text_width(self, text: &str) -> i32 {
        display::text_width(text, self.0)
    }

    pub fn char_width(self, ch: char) -> i32 {
        display::char_width(ch, self.0)
    }

    pub fn text_height(self) -> i32 {
        display::text_height(self.0)
    }

    pub fn line_height(self) -> i32 {
        constant::LINE_SPACE + self.text_height()
    }

    pub fn get_glyph(self, ch: char) -> Option<Glyph> {
        let gl_data = display::get_char_glyph(ch, self.0);

        if gl_data.is_null() {
            return None;
        }

        unsafe {
            let width = *gl_data.offset(0) as i32;
            let height = *gl_data.offset(1) as i32;
            let adv = *gl_data.offset(2) as i32;
            let bearing_x = *gl_data.offset(3) as i32;
            let bearing_y = *gl_data.offset(4) as i32;
            let data = gl_data.offset(5);
            Some(Glyph::new(width, height, adv, bearing_x, bearing_y, data))
        }
    }

    pub fn display_text(
        self,
        text: &'static str,
        baseline: Point,
        fg_color: Color,
        bg_color: Color,
    ) {
        let colortable = get_color_table(fg_color, bg_color);
        let mut adv_total = 0;
        for c in text.chars() {
            let g = self.get_glyph(c);
            if let Some(gly) = g {
                let adv = gly.print(baseline + Offset::new(adv_total, 0), colortable);
                adv_total += adv;
            }
        }
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

    pub fn to_u16(self) -> u16 {
        self.0
    }

    pub fn negate(self) -> Self {
        Self(!self.0)
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

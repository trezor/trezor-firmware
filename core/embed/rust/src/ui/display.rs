use super::constant;
use crate::trezorhal::{time, uzlib};
use crate::{time::Duration, trezorhal::display};
use core::cmp::{max, min};

use super::geometry::{Offset, Point, Rect};

pub fn clamp_coords(r: Rect) -> Rect {
    let x0 = max(r.x0, 0);
    let y0 = max(r.y0, 0);
    let x1 = min(r.x1, constant::WIDTH);
    let y1 = min(r.y1, constant::HEIGHT);

    Rect::new(Point::new(x0, y0), Point::new(x1, y1))
}

pub fn adjust_offset(r: Rect) -> Rect {
    let offset = display::get_offset();
    let p = r.top_left() + Offset::new(offset.0, offset.1);
    return Rect::from_top_left_and_size(p, r.size());
}

pub fn backlight() -> i32 {
    display::backlight(-1)
}

pub fn set_backlight(val: i32) {
    display::backlight(val);
}

pub fn fadein() {
    display::fadein()
}

pub fn fadeout() {
    display::fadeout()
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

pub fn icon_rust(center: Point, data: &[u8], fg_color: Color, bg_color: Color) {
    let toif_info = display::toif_info(data).unwrap();
    assert!(toif_info.grayscale);

    let r = Rect::from_center_and_size(
        center,
        Offset::new(toif_info.width.into(), toif_info.height.into()),
    );

    let area = adjust_offset(r);
    let clamped = clamp_coords(area);
    let colortable = get_color_table(fg_color, bg_color);

    set_window(clamped);

    let mut window = [0_u8; uzlib::UZLIB_WINDOW_SIZE];
    let mut decomp: uzlib::uzlib_uncomp = uzlib::uzlib_uncomp::default();
    let mut dest = [0_u8; 1];

    uzlib::uzlib_prepare(&mut decomp, Some(&mut window), &data[12..], &mut dest);

    let mut prev_data = 0;

    for py in area.y0..area.y1 {
        for px in area.x0..area.x1 {
            let x = px - area.x0;

            if px >= clamped.x0 && px < clamped.x1 && py >= clamped.y0 && py < clamped.y1 {
                if x % 2 == 0 {
                    uzlib::uzlib_uncompress(&mut decomp, &mut dest);
                    prev_data = dest[0];
                    pixeldata(colortable[(prev_data >> 4) as usize]);
                } else {
                    pixeldata(colortable[(prev_data & 0xF) as usize]);
                }
            } else {
                if x % 2 == 0 {
                    //continue unzipping but dont write to display
                    uzlib::uzlib_uncompress(&mut decomp, &mut dest);
                    prev_data = dest[0];
                }
            }
        }
    }

    pixeldata_dirty();
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

#[derive(Copy, Clone, PartialEq, Eq)]
pub struct TextOverlay {
    colortable: [Color; 16],
    area: Rect,
    text: &'static str,
    font: Font,
}

impl TextOverlay {
    pub fn new(bg_color: Color, fg_color: Color, text: &'static str, font: Font) -> Self {
        let area = Rect::zero();
        Self {
            colortable: get_color_table(fg_color, bg_color),
            area,
            text,
            font,
        }
    }

    // baseline relative to the underlying render area
    pub fn place(&mut self, baseline: Offset) {
        let text_width = self.font.text_width(self.text);
        let text_height = self.font.text_height();

        let bl_left = baseline - Offset::x(text_width / 2);
        let text_area_start = Point::new(0, -text_height) + bl_left;
        let text_area_end = Point::new(text_width, 0) + bl_left;
        let area = Rect::new(text_area_start, text_area_end);

        self.area = area;
    }

    pub fn get_pixel(&self, underlying: Option<Color>, x: i32, y: i32) -> Option<Color> {
        let mut overlay_color = None;

        if x >= self.area.x0 && x < self.area.x1 && y >= self.area.y0 && y < self.area.y1 {
            let mut tot_adv = 0;
            let x_t = x - self.area.x0;
            let y_t = y - self.area.y0;

            for c in self.text.chars() {
                if let Some(g) = self.font.get_glyph(c) {
                    let w = g.get_width();
                    let h = g.get_height();
                    let b_x = g.get_bearing_x();
                    let b_y = g.get_bearing_y();

                    if x_t >= (tot_adv + b_x)
                        && x_t < (tot_adv + b_x + w)
                        && y_t >= (h - b_y)
                        && y_t <= (b_y)
                    {
                        //position is for this char
                        let overlay_data = g.get_pixel_data(x_t - tot_adv - b_x, y_t - (h - b_y));

                        if overlay_data > 0 {
                            if let Some(u) = underlying {
                                overlay_color = Some(interpolate_colors(
                                    self.colortable[15],
                                    u,
                                    overlay_data as u16,
                                ));
                            } else {
                                overlay_color = Some(self.colortable[overlay_data as usize]);
                            }
                        }
                        break;
                    }
                    tot_adv += g.get_advance();
                }
            }
        }

        overlay_color
    }
}

#[inline(always)]
fn get_vector(angle: i32) -> (i32, i32) {
    let adj = (100 * (angle % 90)) / 90;

    return if angle >= 0 && angle < 90 {
        (adj, 100 - adj)
    } else if angle >= 90 && angle < 180 {
        (100 - adj, -adj)
    } else if angle >= 180 && angle < 270 {
        (-adj, -100 + adj)
    } else {
        (-100 + adj, adj)
    };
}

#[inline(always)]
fn is_clockwise_or_equal(n_v1: (i32, i32), v2: (i32, i32)) -> bool {
    let psize = v2.0 * n_v1.0 + v2.1 * n_v1.1;
    psize < 0
}

#[inline(always)]
fn is_clockwise_or_equal_inc(n_v1: (i32, i32), v2: (i32, i32)) -> bool {
    let psize = v2.0 * n_v1.0 + v2.1 * n_v1.1;
    psize <= 0
}

pub fn rect_rounded2_partial(
    area: Rect,
    fg_color: Color,
    bg_color: Color,
    show_percent: i32,
    icon: Option<(&[u8], Color)>,
) {
    const MAX_ICON_SIZE: u16 = 64;

    let r = adjust_offset(area);
    let clamped = clamp_coords(r);

    set_window(clamped);

    let center = r.center();
    let colortable = get_color_table(fg_color, bg_color);
    let mut icon_colortable = colortable.clone();

    let mut use_icon = false;
    let mut icon_area = Rect::zero();
    let mut icon_area_clamped = Rect::zero();
    let mut icon_data = [0_u8; ((MAX_ICON_SIZE * MAX_ICON_SIZE) / 2) as usize];
    let mut icon_width = 0;

    if let Some(i) = icon {
        let toif_info = display::toif_info(i.0).unwrap();
        assert!(toif_info.grayscale);

        if toif_info.width <= MAX_ICON_SIZE && toif_info.height <= MAX_ICON_SIZE {
            icon_area = Rect::from_center_and_size(
                center,
                Offset::new(toif_info.width.into(), toif_info.height.into()),
            );
            icon_area_clamped = clamp_coords(icon_area);
            let mut decomp = uzlib::uzlib_uncomp::default();
            uzlib::uzlib_prepare(&mut decomp, None, &i.0[12..], &mut icon_data);
            uzlib::uzlib_uncompress(&mut decomp, &mut icon_data);
            icon_colortable = get_color_table(i.1, bg_color);
            icon_width = toif_info.width.into();
            use_icon = true;
        }
    }

    let start = 0;
    let end = (start + ((360 * show_percent) / 100)) % 360;

    let start_vector;
    let end_vector;

    let mut show_all = false;
    let mut inverted = false;

    if show_percent >= 100 {
        show_all = true;
        start_vector = (0, 0);
        end_vector = (0, 0);
    } else if show_percent > 50 {
        inverted = true;
        start_vector = get_vector(end);
        end_vector = get_vector(start);
    } else {
        start_vector = get_vector(start);
        end_vector = get_vector(end);
    }

    let n_start = (-start_vector.1, start_vector.0);

    for y_c in r.y0..r.y1 {
        for x_c in r.x0..r.x1 {
            let mut icon_pixel = false;
            if use_icon {
                if x_c >= icon_area_clamped.x0
                    && x_c < icon_area_clamped.x1
                    && y_c >= icon_area_clamped.y0
                    && y_c < icon_area_clamped.y1
                {
                    let x_i = x_c - icon_area.x0;
                    let y_i = y_c - icon_area.y0;

                    let data = icon_data[(((x_i & 0xFE) + (y_i * icon_width)) / 2) as usize];
                    if (x_i & 0x01) == 0 {
                        pixeldata(icon_colortable[(data >> 4) as usize]);
                    } else {
                        pixeldata(icon_colortable[(data & 0xF) as usize]);
                    }
                    icon_pixel = true;
                }
            }

            if x_c < clamped.x0
                || x_c >= clamped.x1
                || y_c < clamped.y0
                || y_c >= clamped.y1
                || icon_pixel
            {
                continue;
            }

            if !icon_pixel {
                let y_p = -(y_c - center.y);
                let x_p = x_c - center.x;

                let vx = (x_p, y_p);
                let n_vx = (-y_p, x_p);

                let is_past_start = is_clockwise_or_equal(n_start, vx);
                let is_before_end = is_clockwise_or_equal_inc(n_vx, end_vector);

                if show_all
                    || (!inverted && (is_past_start && is_before_end))
                    || (inverted && !(is_past_start && is_before_end))
                {
                    let y = y_c - r.y0;
                    let x = x_c - r.x0;
                    let c =
                        rect_rounded2_get_pixel(x, y, r.width(), r.height(), colortable, false, 2);
                    pixeldata(c);
                } else {
                    pixeldata(bg_color);
                }
            }
        }
    }

    pixeldata_dirty();
}

pub fn rect_rounded2_get_pixel(
    x: i32,
    y: i32,
    w: i32,
    h: i32,
    colortable: [Color; 16],
    fill: bool,
    line_width: i32,
) -> Color {
    let mut border = false;
    let mut corner_out = false;
    let mut corner_pix = false;

    if (x >= 0 && x < line_width) || ((x >= w - line_width) && x <= (w - 1)) {
        border = true;
    }
    if (y >= 0 && y < line_width) || ((y >= h - line_width) && y <= (h - 1)) {
        border = true;
    }

    let corner_lim = 2 * line_width;
    let corner_pix_lim = 1 * line_width;

    if x < corner_lim && y < corner_lim {
        if x < corner_pix_lim || y < corner_pix_lim {
            corner_out = true;
        } else {
            corner_pix = true;
        }
    }
    if x < corner_lim && y > h - (corner_lim + 1) {
        if x < corner_pix_lim || y > h - (corner_pix_lim + 1) {
            corner_out = true;
        } else {
            corner_pix = true;
        }
    }
    if x > w - (corner_lim + 1) && y < corner_lim {
        if x > w - (corner_pix_lim + 1) || y < corner_pix_lim {
            corner_out = true;
        } else {
            corner_pix = true;
        }
    }
    if x > w - (corner_lim + 1) && y > h - (corner_lim + 1) {
        if x > w - (corner_pix_lim + 1) || y > h - (corner_pix_lim + 1) {
            corner_out = true;
        } else {
            corner_pix = true;
        }
    }

    return if corner_out {
        colortable[0]
    } else if border || corner_pix {
        colortable[15]
    } else {
        if fill {
            colortable[15]
        } else {
            colortable[0]
        }
    };
}

pub fn bar_with_text_and_fill(
    area: Rect,
    overlay: Option<TextOverlay>,
    fg_color: Color,
    bg_color: Color,
    fill_from: i32,
    fill_to: i32,
) {
    let r = adjust_offset(area);
    let clamped = clamp_coords(r);
    let colortable = get_color_table(fg_color, bg_color);

    set_window(clamped);

    for y_c in clamped.y0..clamped.y1 {
        for x_c in clamped.x0..clamped.x1 {
            let y = y_c - r.y0;
            let x = x_c - r.x0;

            let filled =
                (x >= fill_from && fill_from >= 0 && (x <= fill_to || fill_to < fill_from))
                    || (x < fill_to && fill_to >= 0);

            let underlying_color =
                rect_rounded2_get_pixel(x, y, r.width(), r.height(), colortable, filled, 1);

            let mut overlay_color = None;
            if let Some(o) = overlay {
                overlay_color = o.get_pixel(None, x, y);
            }

            let mut final_color = underlying_color;

            if let Some(overlay) = overlay_color {
                if overlay == fg_color {
                    final_color = underlying_color.negate();
                }
            }

            pixeldata(final_color);
        }
    }
    pixeldata_dirty();
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
    let cr: u16;
    let cg: u16;
    let cb: u16;

    cr = ((color0.r() as u16) * step + (color1.r() as u16) * (15 - step)) / 15;
    cg = ((color0.g() as u16) * step + (color1.g() as u16) * (15 - step)) / 15;
    cb = ((color0.b() as u16) * step + (color1.b() as u16) * (15 - step)) / 15;

    return Color::rgb(cr as u8, cg as u8, cb as u8);
}

pub fn get_color_table(fg_color: Color, bg_color: Color) -> [Color; 16] {
    let mut table: [Color; 16] = [Color::from_u16(0); 16];

    for i in 0..16 {
        table[i] = interpolate_colors(fg_color, bg_color, i as u16);
    }

    table
}

pub fn text_top_left(position: Point, text: &str, font: Font, fg_color: Color, bg_color: Color) {
    // let w = font.text_width(text);
    let h = font.text_height();
    display::text(
        position.x,
        position.y + h,
        text,
        font.0,
        fg_color.into(),
        bg_color.into(),
    );
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
        let r = Rect::from_top_left_and_size(pos_adj, size);

        let area = adjust_offset(r);
        let window = clamp_coords(area);

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
            let c_data = self.data.clone().offset((a / 8) as isize);
            let c = ((*c_data >> (7 - (a % 8) * 1)) & 0x01) * 15;
            c
        }
    }

    pub fn unpack_bpp2(&self, a: i32) -> u8 {
        unsafe {
            let c_data = self.data.clone().offset((a / 4) as isize);
            let c = ((*c_data >> (6 - (a % 4) * 2)) & 0x03) * 5;
            c
        }
    }

    pub fn unpack_bpp4(&self, a: i32) -> u8 {
        unsafe {
            let c_data = self.data.clone().offset((a / 2) as isize);
            let c = (*c_data >> (4 - (a % 2) * 4)) & 0x0F;
            c
        }
    }

    pub fn unpack_bpp8(&self, a: i32) -> u8 {
        unsafe {
            let c_data = self.data.clone().offset((a) as isize);
            let c = *c_data >> 4;
            c
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
            return Some(Glyph::new(width, height, adv, bearing_x, bearing_y, data));
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

#[macro_export]
macro_rules! alpha {
    ($n: expr) => {
        if ($n >= 1.0) {
            256_u16
        } else {
            ($n * 256.0) as u16
        }
    };
}

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

    pub const fn rgba(bg: Color, r: u8, g: u8, b: u8, alpha: u16) -> Self {
        let r_u16 = r as u16;
        let g_u16 = g as u16;
        let b_u16 = b as u16;

        let r = ((256 - alpha) * bg.r() as u16 + alpha * r_u16) >> 8;
        let g = ((256 - alpha) * bg.g() as u16 + alpha * g_u16) >> 8;
        let b = ((256 - alpha) * bg.b() as u16 + alpha * b_u16) >> 8;

        let r = (r & 0xF8) << 8;
        let g = (g & 0xFC) << 3;
        let b = (b & 0xF8) >> 3;
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

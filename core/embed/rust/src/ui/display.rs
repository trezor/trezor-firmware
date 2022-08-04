use super::{
    constant,
    font_multiplier::magnify_font,
    geometry::{Offset, Point, Rect},
};
use crate::{
    error::Error,
    time::Duration,
    trezorhal::{
        display, qr, time,
        uzlib::{UzlibContext, UZLIB_WINDOW_SIZE},
    },
    ui::lerp::Lerp,
};
use core::slice;
use heapless::Vec;

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

/// Fill a whole rectangle with a specific color.
pub fn rect_fill(r: Rect, fg_color: Color) {
    display::bar(r.x0, r.y0, r.width(), r.height(), fg_color.into());
}

pub fn rect_stroke(r: Rect, fg_color: Color) {
    display::bar(r.x0, r.y0, r.width(), 1, fg_color.into());
    display::bar(r.x0, r.y0 + r.height() - 1, r.width(), 1, fg_color.into());
    display::bar(r.x0, r.y0, 1, r.height(), fg_color.into());
    display::bar(r.x0 + r.width() - 1, r.y0, 1, r.height(), fg_color.into());
}

/// Draw a rectangle with rounded corners.
pub fn rect_fill_rounded(r: Rect, fg_color: Color, bg_color: Color, radius: u8) {
    if radius == 1 {
        rect_fill_rounded1(r, fg_color, bg_color);
    } else {
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
}

/// Get `width` and `height` of the toif icon/image.
/// Asserts the `grayscale` attribute of the icon/image.
pub fn toif_dimensions(data: &[u8], grayscale: bool) -> (u16, u16) {
    let toif_info = unwrap!(display::toif_info(data), "Invalid TOIF data");
    assert!(toif_info.grayscale == grayscale);
    (toif_info.width, toif_info.height)
}

/// NOTE: Cannot start at odd x-coordinate. In this case icon is shifted 1px
/// left.
pub fn icon_top_left(top_left: Point, data: &[u8], fg_color: Color, bg_color: Color) {
    let (width, height) = toif_dimensions(data, true);
    display::icon(
        top_left.x,
        top_left.y,
        width.into(),
        height.into(),
        &data[12..], // Skip TOIF header.
        fg_color.into(),
        bg_color.into(),
    );
}

/// Display icon given a center Point.
pub fn icon(center: Point, data: &[u8], fg_color: Color, bg_color: Color) {
    let (width, height) = toif_dimensions(data, true);

    let r = Rect::from_center_and_size(center, Offset::new(width.into(), height.into()));
    icon_rect(r, data, fg_color, bg_color);
}

/// Display icon at a specified Rectangle.
pub fn icon_rect(r: Rect, data: &[u8], fg_color: Color, bg_color: Color) {
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
    let (width, height) = toif_dimensions(data, true);

    let r = Rect::from_center_and_size(center, Offset::new(width.into(), height.into()));

    let area = r.translate(get_offset());
    let clamped = area.clamp(constant::screen());
    let colortable = get_color_table(fg_color, bg_color);

    set_window(clamped);

    let mut dest = [0_u8; 1];

    let mut window = [0; UZLIB_WINDOW_SIZE];
    let mut ctx = UzlibContext::new(&data[12..], Some(&mut window));

    for py in area.y0..area.y1 {
        for px in area.x0..area.x1 {
            let p = Point::new(px, py);
            let x = p.x - area.x0;

            if clamped.contains(p) {
                if x % 2 == 0 {
                    unwrap!(ctx.uncompress(&mut dest), "Decompression failed");
                    pixeldata(colortable[(dest[0] >> 4) as usize]);
                } else {
                    pixeldata(colortable[(dest[0] & 0xF) as usize]);
                }
            } else if x % 2 == 0 {
                //continue unzipping but dont write to display
                unwrap!(ctx.uncompress(&mut dest), "Decompression failed");
            }
        }
    }

    pixeldata_dirty();
}

pub fn image(center: Point, data: &[u8]) {
    let (width, height) = toif_dimensions(data, false);

    let r = Rect::from_center_and_size(center, Offset::new(width.into(), height.into()));
    display::image(
        r.x0,
        r.y0,
        r.width(),
        r.height(),
        &data[12..], // Skip TOIF header.
    );
}

pub fn toif_info(data: &[u8]) -> Option<(Offset, bool)> {
    if let Ok(info) = display::toif_info(data) {
        Some((
            Offset::new(info.width.into(), info.height.into()),
            info.grayscale,
        ))
    } else {
        None
    }
}

/// Filling a rectangle with a rounding of 1 pixel - removing the corners.
pub fn rect_fill_rounded1(r: Rect, fg_color: Color, bg_color: Color) {
    rect_fill(r, fg_color);
    rect_fill_corners(r, bg_color);
}

/// Creating a rectangular outline with a given radius/rounding.
pub fn rect_outline_rounded(r: Rect, fg_color: Color, bg_color: Color, radius: u8) {
    // Painting a bigger rectangle with FG and inner smaller with BG
    // to create the outline.
    let inner_r = r.shrink(1);
    if radius == 1 {
        rect_fill_rounded(r, fg_color, bg_color, 1);
        rect_fill(inner_r, bg_color);
    } else if radius == 2 {
        rect_fill_rounded(r, fg_color, bg_color, 2);
        rect_fill_rounded(inner_r, bg_color, fg_color, 1);
    } else if radius == 4 {
        rect_fill_rounded(r, fg_color, bg_color, 4);
        rect_fill_rounded(inner_r, bg_color, fg_color, 2);
        rect_fill_corners(inner_r, bg_color);
    }
}

/// Filling all four corners of a rectangle with a given color.
pub fn rect_fill_corners(r: Rect, fg_color: Color) {
    for p in r.corner_points().iter() {
        paint_point(p, fg_color);
    }
}

#[derive(Copy, Clone, PartialEq, Eq)]
pub struct TextOverlay<T> {
    area: Rect,
    text: T,
    font: Font,
}

impl<T: AsRef<str>> TextOverlay<T> {
    pub fn new(text: T, font: Font) -> Self {
        let area = Rect::zero();
        Self { area, text, font }
    }

    pub fn set_text(&mut self, text: T) {
        self.text = text;
    }

    // baseline relative to the underlying render area
    pub fn place(&mut self, baseline: Point) {
        let text_width = self.font.text_width(self.text.as_ref());
        let text_height = self.font.text_height();

        let text_area_start = baseline + Offset::new(-(text_width / 2), -text_height);
        let text_area_end = baseline + Offset::new(text_width / 2, 0);
        let area = Rect::new(text_area_start, text_area_end);

        self.area = area;
    }

    pub fn get_pixel(&self, underlying: Color, fg: Color, p: Point) -> Color {
        if !self.area.contains(p) {
            return underlying;
        }

        let mut tot_adv = 0;

        let p_rel = Point::new(p.x - self.area.x0, p.y - self.area.y0);

        for g in self
            .text
            .as_ref()
            .bytes()
            .filter_map(|c| self.font.get_glyph(c))
        {
            let char_area = Rect::new(
                Point::new(tot_adv + g.bearing_x, g.height - g.bearing_y),
                Point::new(tot_adv + g.bearing_x + g.width, g.bearing_y),
            );

            tot_adv += g.adv;

            if !char_area.contains(p_rel) {
                continue;
            }

            let p_inner = p_rel - char_area.top_left();
            let overlay_data = g.get_pixel_data(p_inner);
            return Color::lerp(underlying, fg, overlay_data as f32 / 15_f32);
        }

        underlying
    }
}

/// Performs a conversion from `angle` (in degrees) to a vector (`Point`)
/// (polar to cartesian transformation)
/// Suitable for cases where we don't care about distance, it is assumed 1000
///
/// The implementation could be replaced by (cos(`angle`), sin(`angle`)),
/// if we allow trigonometric functions.
/// In the meantime, approximate this with predefined octagon
fn get_vector(angle: i32) -> Point {
    //octagon vertices
    let v = [
        Point::new(0, 1000),
        Point::new(707, 707),
        Point::new(1000, 0),
        Point::new(707, -707),
        Point::new(0, -1000),
        Point::new(-707, -707),
        Point::new(-1000, 0),
        Point::new(-707, 707),
    ];

    let angle = angle % 360;
    let vertices = v.len() as i32;
    let sector_length = 360 / vertices; // only works if 360 is divisible by vertices
    let sector = angle / sector_length;
    let sector_angle = (angle % sector_length) as f32;
    let v1 = v[sector as usize];
    let v2 = v[((sector + 1) % vertices) as usize];
    Point::lerp(v1, v2, sector_angle / sector_length as f32)
}

/// Find whether vector `v2` is clockwise to another vector v1
/// `n_v1` is counter clockwise normal vector to v1
/// ( if v1=(x1,y1), then the counter-clockwise normal is n_v1=(-y1,x1)
#[inline(always)]
fn is_clockwise_or_equal(n_v1: Point, v2: Point) -> bool {
    let psize = v2.x * n_v1.x + v2.y * n_v1.y;
    psize < 0
}

/// Find whether vector v2 is clockwise or equal to another vector v1
/// `n_v1` is counter clockwise normal vector to v1
/// ( if v1=(x1,y1), then the counter-clockwise normal is n_v1=(-y1,x1)
#[inline(always)]
fn is_clockwise_or_equal_inc(n_v1: Point, v2: Point) -> bool {
    let psize = v2.x * n_v1.x + v2.y * n_v1.y;
    psize <= 0
}

/// Draw a rounded rectangle with corner radius 2
/// Draws only a part (sector of a corresponding circe)
/// of the rectangle according to `show_percent` argument,
/// and optionally draw an `icon` inside
pub fn rect_rounded2_partial(
    area: Rect,
    fg_color: Color,
    bg_color: Color,
    show_percent: i32,
    icon: Option<(&[u8], Color)>,
) {
    const MAX_ICON_SIZE: u16 = 64;

    let r = area.translate(get_offset());
    let clamped = r.clamp(constant::screen());

    set_window(clamped);

    let center = r.center();
    let colortable = get_color_table(fg_color, bg_color);
    let mut icon_colortable = colortable;

    let mut use_icon = false;
    let mut icon_area = Rect::zero();
    let mut icon_area_clamped = Rect::zero();
    let mut icon_data = [0_u8; ((MAX_ICON_SIZE * MAX_ICON_SIZE) / 2) as usize];
    let mut icon_width = 0;

    if let Some((icon_bytes, icon_color)) = icon {
        let toif_info = unwrap!(display::toif_info(icon_bytes), "Invalid TOIF data");
        assert!(toif_info.grayscale);

        if toif_info.width <= MAX_ICON_SIZE && toif_info.height <= MAX_ICON_SIZE {
            icon_area = Rect::from_center_and_size(
                center,
                Offset::new(toif_info.width.into(), toif_info.height.into()),
            );
            icon_area_clamped = icon_area.clamp(constant::screen());

            let mut ctx = UzlibContext::new(&icon_bytes[12..], None);
            unwrap!(ctx.uncompress(&mut icon_data), "Decompression failed");
            icon_colortable = get_color_table(icon_color, bg_color);
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
        start_vector = Point::zero();
        end_vector = Point::zero();
    } else if show_percent > 50 {
        inverted = true;
        start_vector = get_vector(end);
        end_vector = get_vector(start);
    } else {
        start_vector = get_vector(start);
        end_vector = get_vector(end);
    }

    let n_start = Point::new(-start_vector.y, start_vector.x);

    for y_c in r.y0..r.y1 {
        for x_c in r.x0..r.x1 {
            let p = Point::new(x_c, y_c);

            let mut icon_pixel = false;
            if use_icon && icon_area_clamped.contains(p) {
                let x_i = p.x - icon_area.x0;
                let y_i = p.y - icon_area.y0;

                let data = icon_data[(((x_i & 0xFE) + (y_i * icon_width)) / 2) as usize];
                if (x_i & 0x01) == 0 {
                    pixeldata(icon_colortable[(data >> 4) as usize]);
                } else {
                    pixeldata(icon_colortable[(data & 0xF) as usize]);
                }
                icon_pixel = true;
            }

            if !clamped.contains(p) || icon_pixel {
                continue;
            }

            let y_p = -(p.y - center.y);
            let x_p = p.x - center.x;

            let vx = Point::new(x_p, y_p);
            let n_vx = Point::new(-y_p, x_p);

            let is_past_start = is_clockwise_or_equal(n_start, vx);
            let is_before_end = is_clockwise_or_equal_inc(n_vx, end_vector);

            if show_all
                || (!inverted && (is_past_start && is_before_end))
                || (inverted && !(is_past_start && is_before_end))
            {
                let p_b = p - r.top_left();
                let c = rect_rounded2_get_pixel(p_b, r.size(), colortable, false, 2);
                pixeldata(c);
            } else {
                pixeldata(bg_color);
            }
        }
    }

    pixeldata_dirty();
}

/// Gets a color of a pixel on `p` coordinates of rounded rectangle with corner
/// radius 2
fn rect_rounded2_get_pixel(
    p: Offset,
    size: Offset,
    colortable: [Color; 16],
    fill: bool,
    line_width: i32,
) -> Color {
    let border = (p.x >= 0 && p.x < line_width)
        || ((p.x >= size.x - line_width) && p.x <= (size.x - 1))
        || (p.y >= 0 && p.y < line_width)
        || ((p.y >= size.y - line_width) && p.y <= (size.y - 1));

    let corner_lim = 2 * line_width;
    let corner_inner = line_width;

    let corner_all = ((p.x > size.x - (corner_lim + 1)) || p.x < corner_lim)
        && (p.y < corner_lim || p.y > size.y - (corner_lim + 1));

    let corner = corner_all
        && (p.y >= corner_inner)
        && (p.x >= corner_inner)
        && (p.y <= size.y - (corner_inner + 1))
        && (p.x <= size.x - (corner_inner + 1));

    let corner_out = corner_all && !corner;

    if (border || corner || fill) && !corner_out {
        colortable[15]
    } else {
        colortable[0]
    }
}

/// Draws a rounded rectangle with corner radius 2, partially filled
/// according to `fill_from` and `fill_to` arguments.
/// Optionally draws a text inside the rectangle and adjusts its color to match
/// the fill. The coordinates of the text are specified in the TextOverlay
/// struct.
pub fn bar_with_text_and_fill<T: AsRef<str>>(
    area: Rect,
    overlay: Option<&TextOverlay<T>>,
    fg_color: Color,
    bg_color: Color,
    fill_from: i32,
    fill_to: i32,
) {
    let r = area.translate(get_offset());
    let clamped = r.clamp(constant::screen());
    let colortable = get_color_table(fg_color, bg_color);

    set_window(clamped);

    for y_c in clamped.y0..clamped.y1 {
        for x_c in clamped.x0..clamped.x1 {
            let p = Point::new(x_c, y_c);
            let r_offset = p - r.top_left();

            let filled = (r_offset.x >= fill_from
                && fill_from >= 0
                && (r_offset.x <= fill_to || fill_to < fill_from))
                || (r_offset.x < fill_to && fill_to >= 0);

            let underlying_color =
                rect_rounded2_get_pixel(r_offset, r.size(), colortable, filled, 1);

            let final_color = overlay.map_or(underlying_color, |o| {
                let text_color = if filled { bg_color } else { fg_color };
                o.get_pixel(underlying_color, text_color, p)
            });

            pixeldata(final_color);
        }
    }
    pixeldata_dirty();
}

/// Draws a horizontal line of pixels with a step of 2 pixels.
pub fn dotted_line_horizontal(start: Point, width: i32, color: Color) {
    for x in (start.x..width).step_by(2) {
        paint_point(&Point::new(x, start.y), color);
    }
}

/// Paints a pixel with a specific color on a given point.
pub fn paint_point(point: &Point, color: Color) {
    display::bar(point.x, point.y, 1, 1, color.into());
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

pub fn qrcode(center: Point, data: &str, max_size: u32, case_sensitive: bool) -> Result<(), Error> {
    qr::render_qrcode(center.x, center.y, data, max_size, case_sensitive)
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

pub fn get_offset() -> Offset {
    let offset = display::get_offset();
    Offset::new(offset.0, offset.1)
}

pub fn set_window(window: Rect) {
    display::set_window(
        window.x0 as u16,
        window.y0 as u16,
        window.x1 as u16 - 1,
        window.y1 as u16 - 1,
    );
}

pub fn get_color_table(fg_color: Color, bg_color: Color) -> [Color; 16] {
    let mut table: [Color; 16] = [Color::from_u16(0); 16];

    for (i, item) in table.iter_mut().enumerate() {
        *item = Color::lerp(bg_color, fg_color, i as f32 / 15_f32);
    }

    table
}

pub struct Glyph {
    pub width: i32,
    pub height: i32,
    pub adv: i32,
    pub bearing_x: i32,
    pub bearing_y: i32,
    data: &'static [u8],
}

impl Glyph {
    /// Construct a `Glyph` from a raw pointer.
    ///
    /// # Safety
    ///
    /// This function is unsafe because the caller has to guarantee that `data`
    /// is pointing to a memory containing a valid glyph data, that is:
    /// - contains valid glyph metadata
    /// - data has appropriate size
    /// - data must have static lifetime
    pub unsafe fn load(data: *const u8) -> Self {
        unsafe {
            let width = *data.offset(0) as i32;
            let height = *data.offset(1) as i32;

            let data_bits = constant::FONT_BPP * width * height;

            let data_bytes = if data_bits % 8 == 0 {
                data_bits / 8
            } else {
                (data_bits / 8) + 1
            };

            Glyph {
                width,
                height,
                adv: *data.offset(2) as i32,
                bearing_x: *data.offset(3) as i32,
                bearing_y: *data.offset(4) as i32,
                data: slice::from_raw_parts(data.offset(5), data_bytes as usize),
            }
        }
    }

    pub fn print(&self, pos: Point, colortable: [Color; 16]) -> i32 {
        let bearing = Offset::new(self.bearing_x, -self.bearing_y);
        let size = Offset::new(self.width, self.height);
        let pos_adj = pos + bearing;
        let r = Rect::from_top_left_and_size(pos_adj, size);

        let area = r.translate(get_offset());
        let window = area.clamp(constant::screen());

        set_window(window);

        for y in window.y0..window.y1 {
            for x in window.x0..window.x1 {
                let p = Point::new(x, y);
                let r = p - pos_adj;
                let c = self.get_pixel_data(r);
                pixeldata(colortable[c as usize]);
            }
        }
        self.adv
    }

    /// Returns 0 (black) or 15 (white).
    pub fn unpack_bpp1(&self, a: i32) -> u8 {
        let c_data = self.data[(a / 8) as usize];
        ((c_data >> (7 - (a % 8))) & 0x01) * 15
    }

    pub fn unpack_bpp2(&self, a: i32) -> u8 {
        let c_data = self.data[(a / 4) as usize];
        ((c_data >> (6 - (a % 4) * 2)) & 0x03) * 5
    }

    pub fn unpack_bpp4(&self, a: i32) -> u8 {
        let c_data = self.data[(a / 2) as usize];
        (c_data >> (4 - (a % 2) * 4)) & 0x0F
    }

    pub fn unpack_bpp8(&self, a: i32) -> u8 {
        let c_data = self.data[a as usize];
        c_data >> 4
    }

    pub fn get_pixel_data(&self, p: Offset) -> u8 {
        let a = p.x + p.y * self.width;

        match constant::FONT_BPP {
            1 => self.unpack_bpp1(a),
            2 => self.unpack_bpp2(a),
            4 => self.unpack_bpp4(a),
            8 => self.unpack_bpp8(a),
            _ => 0,
        }
    }
}

// TODO: could be connected with regular `Glyph`,
// as there is a lot of duplication - most attributes,
// `print` method etc.
// For that to happen, `Glyph` would need to have
// a field `magnification`, being `1` by default.
// Also, we would need to unify the data type -
// `Glyph` uses pointer to bytes data, this uses
// local vector of bits.
// However, the current method of magnification
// probably only works for 1bpp colors. Or not?
// TODO: implement the magnifying in print(), it will remove a lot of complexity.
pub struct MagnifiedGlyph1BPP {
    width: i32,
    height: i32,
    adv: i32,
    bearing_x: i32,
    bearing_y: i32,
    // TODO: how to handle the maximum allocation?
    data: Vec<bool, 1280>,
}

impl MagnifiedGlyph1BPP {
    pub fn new(
        width: i32,
        height: i32,
        adv: i32,
        bearing_x: i32,
        bearing_y: i32,
        data: Vec<bool, 1280>,
    ) -> Self {
        MagnifiedGlyph1BPP {
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

        let area = r.translate(get_offset());
        let window = area.clamp(constant::screen());

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

    pub fn get_pixel_data(&self, x: i32, y: i32) -> u8 {
        let index = x + y * self.width;
        let pixel = self.data[index as usize];
        if pixel {
            15
        } else {
            0
        }
    }
}

#[derive(Copy, Clone, Debug, PartialEq, Eq)]
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

    pub fn get_glyph(self, char_byte: u8) -> Option<Glyph> {
        let gl_data = display::get_char_glyph(char_byte, self.0);

        if gl_data.is_null() {
            return None;
        }
        unsafe { Some(Glyph::load(gl_data)) }
    }

    pub fn display_text(self, text: &str, baseline: Point, fg_color: Color, bg_color: Color) {
        let colortable = get_color_table(fg_color, bg_color);
        let mut adv_total = 0;
        for c in text.bytes() {
            let g = self.get_glyph(c);
            if let Some(gly) = g {
                let adv = gly.print(baseline + Offset::new(adv_total, 0), colortable);
                adv_total += adv;
            }
        }
    }

    pub fn get_glyph_magnified(self, ch: char, magnification: u8) -> Option<MagnifiedGlyph1BPP> {
        let gl_data = display::get_char_glyph(ch as u8, self.0);

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

            // Extracting the original data
            let bytes_length = (width * height + 8 - 1) / 8; // Getting full bytes - rounding up
            let bytes = slice::from_raw_parts(data, bytes_length as usize);
            let bytes_vec: Vec<u8, 16> = Vec::from_slice(bytes).unwrap();

            // Transforming the glyph to have a bigger size
            let mut magnified_bits: Vec<bool, 1280> = Vec::new();
            magnify_font(magnification, width, height, bytes_vec, &mut magnified_bits);

            // All the properties need to be magnified accordingly as well
            Some(MagnifiedGlyph1BPP::new(
                width * magnification as i32,
                height * magnification as i32,
                adv * magnification as i32,
                bearing_x * magnification as i32,
                bearing_y * magnification as i32,
                magnified_bits,
            ))
        }
    }

    pub fn display_char_magnified(
        self,
        ch: char,
        magnification: u8,
        baseline: Point,
        fg_color: Color,
        bg_color: Color,
    ) -> Option<i32> {
        if constant::FONT_BPP != 1 {
            panic!("Magnification is only supported for 1BPP fonts");
        }

        let colortable = get_color_table(fg_color, bg_color);
        let g = self.get_glyph_magnified(ch, magnification);
        if let Some(gly) = g {
            let advance = gly.print(baseline, colortable);
            return Some(advance);
        }
        None
    }

    pub fn display_text_magnified<T: AsRef<str>>(
        self,
        magnification: u8,
        text: T,
        baseline: Point,
        fg_color: Color,
        bg_color: Color,
    ) {
        let mut adv_total = 0;
        for c in text.as_ref().chars() {
            let advance = self.display_char_magnified(
                c,
                magnification,
                baseline + Offset::new(adv_total, 0),
                fg_color,
                bg_color,
            );
            if let Some(adv) = advance {
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

    pub const fn white() -> Self {
        Self::rgb(255, 255, 255)
    }

    pub const fn black() -> Self {
        Self::rgb(0, 0, 0)
    }
}

impl Lerp for Color {
    fn lerp(a: Self, b: Self, t: f32) -> Self {
        let r = u8::lerp(a.r(), b.r(), t);
        let g = u8::lerp(a.g(), b.g(), t);
        let b = u8::lerp(a.b(), b.b(), t);
        Color::rgb(r, g, b)
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

/// Holding icon data and allowing it to draw itself.
/// Lots of draw methods exist so that we can easily
/// "glue" the icon together with other elements
/// (text, display boundary, etc.) according to their position.
#[derive(Debug, Clone, Copy)]
pub struct Icon<T> {
    pub data: &'static [u8],
    // NOTE: text is here mostly so that we can instantiate
    // HTC with icon, when HTC does not support icons yet.
    // It is also useful for debugging, as this text gets printed.
    // TODO: it might be deleted when HTC supports icons
    pub text: T,
    // TODO: could include the info about "real" icon dimensions,
    // accounting for the TOIF limitations (when we sometimes
    // need to have empty row or column) - it could be
    // erasing those empty rows/columns when we draw the icon.
}

// TODO: consider merging it together with ToifInfo
impl<T> Icon<T>
where
    T: AsRef<str>,
{
    pub fn new(data: &'static [u8], text: T) -> Self {
        Icon { data, text }
    }

    pub fn width(&self) -> i32 {
        toif_dimensions(self.data, true).0 as _
    }

    pub fn height(&self) -> i32 {
        toif_dimensions(self.data, true).1 as _
    }

    pub fn offset_size(&self) -> Offset {
        Offset::new(self.width(), self.height())
    }

    /// Display the icon with left top baseline Point.
    pub fn draw_top_left(&self, baseline: Point, fg_color: Color, bg_color: Color) {
        let r = Rect::from_top_left_and_size(baseline, self.offset_size());
        icon_rect(r, self.data, fg_color, bg_color);
    }

    /// Display the icon with right top baseline Point.
    pub fn draw_top_right(&self, baseline: Point, fg_color: Color, bg_color: Color) {
        let r = Rect::from_top_right_and_size(baseline, self.offset_size());
        icon_rect(r, self.data, fg_color, bg_color);
    }

    /// Display the icon with right bottom baseline Point.
    pub fn draw_bottom_right(&self, baseline: Point, fg_color: Color, bg_color: Color) {
        let r = Rect::from_bottom_right_and_size(baseline, self.offset_size());
        icon_rect(r, self.data, fg_color, bg_color);
    }

    /// Display the icon with left bottom baseline Point.
    pub fn draw_bottom_left(&self, baseline: Point, fg_color: Color, bg_color: Color) {
        let r = Rect::from_bottom_left_and_size(baseline, self.offset_size());
        icon_rect(r, self.data, fg_color, bg_color);
    }

    /// Display the icon around center Point.
    pub fn draw_center(&self, center: Point, fg_color: Color, bg_color: Color) {
        let r = Rect::from_center_and_size(center, self.offset_size());
        icon_rect(r, self.data, fg_color, bg_color);
    }
}

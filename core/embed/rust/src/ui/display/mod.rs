pub mod color;
pub mod font;
pub mod loader;
#[cfg(feature = "jpeg")]
pub mod tjpgd;
pub mod toif;

use super::{
    constant,
    geometry::{Offset, Point, Rect},
};
#[cfg(feature = "dma2d")]
use crate::trezorhal::{
    dma2d::{
        dma2d_setup_4bpp_over_16bpp, dma2d_setup_4bpp_over_4bpp, dma2d_start_blend,
        dma2d_wait_for_transfer,
    },
    uzlib::UZLIB_WINDOW_SIZE,
};
#[cfg(feature = "dma2d")]
use crate::ui::component::image::Image;

#[cfg(not(feature = "dma2d"))]
use crate::ui::geometry::Alignment2D;

#[cfg(feature = "backlight")]
use crate::{time::Duration, trezorhal::time};

use crate::{
    trezorhal::{buffers, display, uzlib::UzlibContext},
    ui::lerp::Lerp,
};

// Reexports
use crate::trezorhal::buffers::BufferText;
pub use crate::ui::display::toif::Icon;
pub use color::Color;
pub use font::{Font, Glyph, GlyphMetrics};
pub use loader::{
    loader, loader_indeterminate, loader_small_indeterminate, LOADER_MAX, LOADER_MIN,
};

#[cfg(all(feature = "dma2d", feature = "framebuffer"))]
use crate::trezorhal::{
    display::{get_fb_addr, pixel},
    dma2d::{dma2d_setup_const, dma2d_start_const_multiline},
};
use crate::ui::constant::WIDTH;

pub fn backlight() -> u16 {
    display::backlight(-1) as u16
}

#[cfg(feature = "backlight")]
pub fn set_backlight(val: u16) {
    display::backlight(val as i32);
}

#[cfg(feature = "backlight")]
pub fn fade_backlight(target: u16) {
    const FADE_DURATION_MS: u32 = 50;
    fade_backlight_duration(target, FADE_DURATION_MS);
}

#[cfg(feature = "backlight")]
pub fn fade_backlight_duration(target: u16, duration_ms: u32) {
    let target = target as i32;
    let duration_ms = duration_ms as i32;
    let current = backlight() as i32;

    for i in 0..duration_ms {
        let val = i32::lerp(current, target, i as f32 / duration_ms as f32);
        set_backlight(val as u16);
        time::sleep(Duration::from_millis(1));
    }
    //account for imprecise rounding
    set_backlight(target as u16);
}

#[cfg(not(feature = "backlight"))]
pub fn set_backlight(_: u16) {}

#[cfg(not(feature = "backlight"))]
pub fn fade_backlight(_: u16) {}

#[cfg(not(feature = "backlight"))]
pub fn fade_backlight_duration(_: u16, _: u32) {}

#[cfg(not(feature = "framebuffer"))]
/// Fill a whole rectangle with a specific color.
pub fn rect_fill(r: Rect, fg_color: Color) {
    let r = r.translate(get_offset());
    let r = r.clamp(constant::screen());

    set_window(r);

    for _ in r.y0..r.y1 {
        for _ in r.x0..r.x1 {
            pixeldata(fg_color.into());
        }
    }

    pixeldata_dirty();
}

#[cfg(feature = "framebuffer")]
pub fn rect_fill(r: Rect, fg_color: Color) {
    let r = r.translate(get_offset());
    let r = r.clamp(constant::screen());
    set_window(r);
    dma2d_setup_const();
    unsafe {
        dma2d_start_const_multiline(fg_color.into(), r.width(), r.height());
    }
    dma2d_wait_for_transfer();
    pixeldata_dirty();
}

pub fn rect_stroke(r: Rect, fg_color: Color) {
    rect_fill(
        Rect::from_top_left_and_size(Point::new(r.x0, r.y0), Offset::new(r.width(), 1)),
        fg_color,
    );
    rect_fill(
        Rect::from_top_left_and_size(
            Point::new(r.x0, r.y0 + r.height() - 1),
            Offset::new(r.width(), 1),
        ),
        fg_color,
    );
    rect_fill(
        Rect::from_top_left_and_size(Point::new(r.x0, r.y0), Offset::new(1, r.height())),
        fg_color,
    );
    rect_fill(
        Rect::from_top_left_and_size(
            Point::new(r.x0 + r.width() - 1, r.y0),
            Offset::new(1, r.height()),
        ),
        fg_color,
    );
}

const CORNER_RADIUS: usize = 16;

#[rustfmt::skip]
const CORNER_TABLE: [usize; CORNER_RADIUS * CORNER_RADIUS] = [
     0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  1,  5,  9, 12, 14, 15,
     0,  0,  0,  0,  0,  0,  0,  0,  3,  9, 15, 15, 15, 15, 15, 15,
     0,  0,  0,  0,  0,  0,  0,  8, 15, 15, 15, 15, 15, 15, 15, 15,
     0,  0,  0,  0,  0,  3, 12, 15, 15, 15, 15, 15, 15, 15, 15, 15,
     0,  0,  0,  0,  3, 14, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15,
     0,  0,  0,  3, 14, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15,
     0,  0,  0, 12, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15,
     0,  0,  8, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15,
     0,  3, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15,
     0,  9, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15,
     1, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15,
     5, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15,
     9, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15,
    12, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15,
    14, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15,
    15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15,
];

/// Draw a rectangle with rounded corners.
#[cfg(not(feature = "framebuffer"))]
pub fn rect_fill_rounded(r: Rect, fg_color: Color, bg_color: Color, radius: u8) {
    if radius == 1 {
        rect_fill_rounded1(r, fg_color, bg_color);
    } else {
        assert!([2, 4, 8, 16].iter().any(|allowed| radius == *allowed));

        let color_table = get_color_table(fg_color, bg_color);
        let area = r.translate(get_offset());
        let clamped = area.clamp(constant::screen());

        set_window(clamped);

        let radius = radius as i16;
        let radius_inv = 16 / radius;

        for y in area.y0..area.y1 {
            for x in area.x0..area.x1 {
                if x - r.x0 < radius && y - r.y0 < radius {
                    let c = CORNER_TABLE[((x - area.x0) * radius_inv
                        + (y - area.y0) * radius_inv * CORNER_RADIUS as i16)
                        as usize];
                    pixeldata(color_table[c]);
                } else if x - r.x0 < radius && y - r.y0 >= r.height() - radius {
                    let c = CORNER_TABLE[((x - area.x0) * radius_inv
                        + (r.height() - 1 - (y - area.y0)) * radius_inv * CORNER_RADIUS as i16)
                        as usize];
                    pixeldata(color_table[c]);
                } else if x - r.x0 >= r.width() - radius && y - r.y0 < radius {
                    let c = CORNER_TABLE[((r.width() - 1 - (x - area.x0)) * radius_inv
                        + (y - area.y0) * radius_inv * CORNER_RADIUS as i16)
                        as usize];
                    pixeldata(color_table[c]);
                } else if x - r.x0 >= r.width() - radius && y - r.y0 >= r.height() - radius {
                    let c = CORNER_TABLE[((r.width() - 1 - (x - area.x0)) * radius_inv
                        + (r.height() - 1 - (y - area.y0)) * radius_inv * CORNER_RADIUS as i16)
                        as usize];
                    pixeldata(color_table[c]);
                } else {
                    pixeldata(color_table[15]);
                }
            }
        }
    }
    pixeldata_dirty();
}

pub fn rect_fill_rounded_buffer(r: Rect, radius: u8, buffer: &mut BufferText) {
    if r.height() > r.y0 + buffers::TEXT_BUFFER_HEIGHT as i16 || r.x0 + r.width() > WIDTH {
        return;
    }

    assert!([2, 4, 8, 16].iter().any(|allowed| radius == *allowed));

    let radius = radius as i16;
    let radius_inv = 16 / radius;

    for y in r.y0..r.y1 {
        for x in r.x0..r.x1 {
            let c = if x - r.x0 < radius && y - r.y0 < radius {
                CORNER_TABLE[((x - r.x0) * radius_inv
                    + (y - r.y0) * radius_inv * CORNER_RADIUS as i16)
                    as usize]
            } else if x - r.x0 < radius && y - r.y0 >= r.height() - radius {
                CORNER_TABLE[((x - r.x0) * radius_inv
                    + (r.height() - 1 - (y - r.y0)) * radius_inv * CORNER_RADIUS as i16)
                    as usize]
            } else if x - r.x0 >= r.width() - radius && y - r.y0 < radius {
                CORNER_TABLE[((r.width() - 1 - (x - r.x0)) * radius_inv
                    + (y - r.y0) * radius_inv * CORNER_RADIUS as i16)
                    as usize]
            } else if x - r.x0 >= r.width() - radius && y - r.y0 >= r.height() - radius {
                CORNER_TABLE[((r.width() - 1 - (x - r.x0)) * radius_inv
                    + (r.height() - 1 - (y - r.y0)) * radius_inv * CORNER_RADIUS as i16)
                    as usize]
            } else {
                15usize
            };
            let p = y * WIDTH + x;
            let b = (p / 2) as usize;
            if p % 2 != 0 {
                buffer.buffer[b] |= (c << 4) as u8;
            } else {
                buffer.buffer[b] |= c as u8;
            }
        }
    }
    pixeldata_dirty();
}

#[cfg(feature = "framebuffer")]
/// Draw a rectangle with rounded corners.
pub fn rect_fill_rounded(area: Rect, fg_color: Color, bg_color: Color, radius: u8) {
    let radius = radius as i16;
    if radius == 1 {
        rect_fill_rounded1(area, fg_color, bg_color);
    } else {
        assert!([2, 4, 8, 16].iter().any(|allowed| radius == *allowed));

        let r = area.translate(get_offset());
        let r = r.clamp(constant::screen());
        let fb = get_fb_addr();

        rect_fill(r, fg_color);
        let r_inv = 16 / radius;
        let color_table = get_color_table(fg_color, bg_color);

        for y in 0..radius {
            for x in 0..radius {
                let c = CORNER_TABLE[(x * r_inv + y * r_inv * 16) as usize];
                pixel(fb, r.x0 + x, r.y0 + y, color_table[c].into());
            }
        }
        for y in 0..radius {
            for x in 0..radius {
                let c = CORNER_TABLE[((radius - x - 1) * r_inv + y * r_inv * 16) as usize];
                pixel(fb, r.x1 - radius + x, r.y0 + y, color_table[c].into());
            }
        }
        for y in 0..radius {
            for x in 0..radius {
                let c = CORNER_TABLE[(x * r_inv + (radius - y - 1) * r_inv * 16) as usize];
                pixel(fb, r.x0 + x, r.y1 - radius + y, color_table[c].into());
            }
        }
        for y in 0..radius {
            for x in 0..radius {
                let c = CORNER_TABLE
                    [((radius - x - 1) * r_inv + (radius - y - 1) * r_inv * 16) as usize];
                pixel(
                    fb,
                    r.x1 - radius + x,
                    r.y1 - radius + y,
                    color_table[c].into(),
                );
            }
        }
    }
    pixeldata_dirty();
}

/// Filling a rectangle with a rounding of 1 pixel - removing the corners.
fn rect_fill_rounded1(r: Rect, fg_color: Color, bg_color: Color) {
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
        rect_fill_corners(inner_r, fg_color);
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
        // This draws a 1x1 rectangle at the given point.
        rect_fill(
            Rect::from_top_left_and_size(*p, Offset::uniform(1)),
            fg_color,
        );
    }
}

#[derive(Copy, Clone, PartialEq, Eq)]
pub struct TextOverlay<T> {
    area: Rect,
    text: T,
    font: Font,
    max_height: i16,
    baseline: i16,
}

impl<T: AsRef<str>> TextOverlay<T> {
    pub fn new(text: T, font: Font) -> Self {
        let area = Rect::zero();

        Self {
            area,
            text,
            font,
            max_height: font.max_height(),
            baseline: font.text_baseline(),
        }
    }

    pub fn set_text(&mut self, text: T) {
        self.text = text;
    }

    pub fn get_text(&self) -> &T {
        &self.text
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
            let top = self.max_height - self.baseline - g.bearing_y;
            let char_area = Rect::new(
                Point::new(tot_adv + g.bearing_x, top),
                Point::new(tot_adv + g.bearing_x + g.width, top + g.height),
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
fn get_vector(angle: i16) -> Point {
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
    let vertices = v.len() as i16;
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
    let psize = v2.x as i32 * n_v1.x as i32 + v2.y as i32 * n_v1.y as i32;
    psize < 0
}

/// Find whether vector v2 is clockwise or equal to another vector v1
/// `n_v1` is counter clockwise normal vector to v1
/// ( if v1=(x1,y1), then the counter-clockwise normal is n_v1=(-y1,x1)
#[inline(always)]
fn is_clockwise_or_equal_inc(n_v1: Point, v2: Point) -> bool {
    let psize = v2.x as i32 * n_v1.x as i32 + v2.y as i32 * n_v1.y as i32;
    psize <= 0
}

/// Draw a rounded rectangle with corner radius 2
/// Draws only a part (sector of a corresponding circle)
/// of the rectangle according to `show_percent` argument,
/// and optionally draw an `icon` inside
pub fn rect_rounded2_partial(
    area: Rect,
    fg_color: Color,
    bg_color: Color,
    show_percent: i16,
    icon: Option<(Icon, Color)>,
) {
    const MAX_ICON_SIZE: i16 = 64;

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

    if let Some((icon, icon_color)) = icon {
        let icon_size = icon.toif.size();
        if icon_size.x <= MAX_ICON_SIZE && icon_size.y <= MAX_ICON_SIZE {
            icon_area = Rect::from_center_and_size(center, icon_size);
            icon_area_clamped = icon_area.clamp(constant::screen());
            icon.toif.uncompress(&mut icon_data);
            icon_colortable = get_color_table(icon_color, bg_color);
            icon_width = icon.toif.width();
            use_icon = true;
        }
    }

    let start = 0;
    let end = (start + (360 * show_percent as u32) / 100) % 360;

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
        start_vector = get_vector(end as _);
        end_vector = get_vector(start as _);
    } else {
        start_vector = get_vector(start as _);
        end_vector = get_vector(end as _);
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
                    pixeldata(icon_colortable[(data & 0xF) as usize]);
                } else {
                    pixeldata(icon_colortable[(data >> 4) as usize]);
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

/// Shifts position of pixel data in `src_buffer` horizontally by `offset_x`
/// pixels and places the result into `dest_buffer`. Or in another words,
/// `src_buffer[n]` is copied into `dest_buffer[n+offset_x]`, if it fits the
/// `dest_buffer`.
///
/// Buffers hold one line of pixels on the screen, the copying is limited to
/// respect the size of screen.
///
/// `buffer_bpp` determines size of pixel data
/// `data_width` sets the width of valid data in the `src_buffer`
pub(crate) fn position_buffer(
    dest_buffer: &mut [u8],
    src_buffer: &[u8],
    buffer_bpp: usize,
    offset_x: i16,
    data_width: i16,
) {
    let data_width_even = if buffer_bpp == 4 && data_width % 2 != 0 {
        data_width + 1
    } else {
        data_width
    };

    let mut start: usize = (offset_x).clamp(0, constant::WIDTH) as usize;
    let mut end: usize = (offset_x + data_width_even).clamp(0, constant::WIDTH) as usize;

    if buffer_bpp == 4 {
        start &= !0x01;
        end &= !0x01;
    }

    let width = end - start;

    // if the offset is negative, need to skip beginning of uncompressed data
    let x_sh = if offset_x < 0 {
        (-offset_x).clamp(0, constant::WIDTH - width as i16) as usize
    } else {
        0
    };
    dest_buffer[((start * buffer_bpp) / 8)..((start + width) * buffer_bpp) / 8]
        .copy_from_slice(&src_buffer[((x_sh * buffer_bpp) / 8)..((x_sh + width) * buffer_bpp) / 8]);
}

/// Performs decompression of one line of pixels,
/// vertically positions the line against the display area (current position of
/// which is described by `display_area_y`) by skipping relevant number of lines
/// and finally horizontally positions the line against the display area
/// by calling `position_buffer`.
///
/// Number of already decompressed lines is stored in `decompressed_lines` to
/// keep track of how many need to be skipped.
///
/// Signals to the caller whether some data should be drawn on this line.
fn process_buffer(
    display_area_y: i16,
    img_area: Rect,
    offset: Offset,
    ctx: &mut UzlibContext,
    buffer: &mut [u8],
    decompressed_lines: &mut i16,
    buffer_bpp: usize,
) -> bool {
    let mut not_empty = false;
    let uncomp_buffer =
        &mut [0u8; (constant::WIDTH * 2) as usize][..((constant::WIDTH as usize) * buffer_bpp) / 8];

    if display_area_y >= img_area.y0 && display_area_y < img_area.y1 {
        let img_line_idx = display_area_y - img_area.y0;

        while *decompressed_lines < img_line_idx {
            //compensate uncompressed unused lines
            unwrap!(
                ctx.uncompress(
                    &mut uncomp_buffer[0..((img_area.width() * buffer_bpp as i16) / 8) as usize]
                ),
                "Decompression failed"
            );

            (*decompressed_lines) += 1;
        }
        // decompress whole line
        unwrap!(
            ctx.uncompress(
                &mut uncomp_buffer[0..((img_area.width() * buffer_bpp as i16) / 8) as usize]
            ),
            "Decompression failed"
        );

        (*decompressed_lines) += 1;

        position_buffer(
            buffer,
            uncomp_buffer,
            buffer_bpp,
            offset.x,
            img_area.width(),
        );

        not_empty = true;
    }

    not_empty
}

/// Renders text over image background
/// If `bg_area` is given, it is filled with its color in places where there are
/// neither text or image Positioning also depends on whether `bg_area` is
/// provided:
/// - if it is, text and image are positioned relative to the `bg_area` top left
///   corner, using respective offsets. Nothing is drawn outside the `bg_area`.
/// - if it is not, text is positioned relative to the images top left corner
///   using `offset_text` and image is positioned on the screen using
///   `offset_img`. Nothing is drawn outside the image.
/// `offset_text` is interpreted as baseline, so using (0,0) will position most
/// of the text outside the drawing area in either case.
///
/// The drawing area is coerced to even width, which is due to dma2d limitation
/// when using 4bpp
#[cfg(feature = "dma2d")]
pub fn text_over_image(
    bg_area: Option<(Rect, Color)>,
    image: Image,
    text: &str,
    font: Font,
    offset_img: Offset,
    offset_text: Offset,
    text_color: Color,
) {
    let mut text_buffer = buffers::BufferText::get();
    let mut img1 = buffers::BufferLine16bpp::get_cleared();
    let mut img2 = buffers::BufferLine16bpp::get_cleared();
    let mut empty_img = buffers::BufferLine16bpp::get_cleared();
    let mut t1 = buffers::BufferLine4bpp::get_cleared();
    let mut t2 = buffers::BufferLine4bpp::get_cleared();
    let mut empty_t = buffers::BufferLine4bpp::get_cleared();

    let r_img;
    let area;
    let offset_img_final;
    if let Some((a, color)) = bg_area {
        let hi = color.hi_byte();
        let lo = color.lo_byte();
        //prefill image/bg buffers with the bg color
        for i in 0..(constant::WIDTH) as usize {
            img1.buffer[2 * i] = lo;
            img1.buffer[2 * i + 1] = hi;
        }
        img2.buffer.copy_from_slice(&img1.buffer);
        empty_img.buffer.copy_from_slice(&img1.buffer);

        area = a;
        r_img = Rect::from_top_left_and_size(a.top_left() + offset_img, image.toif.size());
        offset_img_final = offset_img;
    } else {
        area = Rect::from_top_left_and_size(offset_img.into(), image.toif.size());
        r_img = area;
        offset_img_final = Offset::zero();
    }
    let clamped = area.clamp(constant::screen()).ensure_even_width();

    let text_width = display::text_width(text, font.into());
    let font_max_height = display::text_max_height(font.into());
    let font_baseline = display::text_baseline(font.into());
    let text_width_clamped = text_width.clamp(0, clamped.width());

    let text_top = area.y0 + offset_text.y - font_max_height + font_baseline;
    let text_bottom = area.y0 + offset_text.y + font_baseline;
    let text_left = area.x0 + offset_text.x;
    let text_right = area.x0 + offset_text.x + text_width_clamped;

    let text_area = Rect::new(
        Point::new(text_left, text_top),
        Point::new(text_right, text_bottom),
    );

    display::text_into_buffer(text, font.into(), &mut text_buffer, 0);

    set_window(clamped);

    let mut window = [0; UZLIB_WINDOW_SIZE];
    let mut ctx = image.toif.decompression_context(Some(&mut window));

    dma2d_setup_4bpp_over_16bpp(text_color.into());

    let mut i = 0;

    for y in clamped.y0..clamped.y1 {
        let mut img_buffer = &mut *empty_img;
        let mut t_buffer = &mut *empty_t;
        let img_buffer_used;
        let t_buffer_used;

        if y % 2 == 0 {
            t_buffer_used = &mut *t1;
            img_buffer_used = &mut *img1;
        } else {
            t_buffer_used = &mut *t2;
            img_buffer_used = &mut *img2;
        }

        let using_img = process_buffer(
            y,
            r_img,
            offset_img_final,
            &mut ctx,
            &mut img_buffer_used.buffer,
            &mut i,
            16,
        );

        if y >= text_area.y0 && y < text_area.y1 {
            let y_pos = y - text_area.y0;
            position_buffer(
                &mut t_buffer_used.buffer,
                &text_buffer.buffer[(y_pos * constant::WIDTH / 2) as usize
                    ..((y_pos + 1) * constant::WIDTH / 2) as usize],
                4,
                offset_text.x,
                text_width,
            );
            t_buffer = t_buffer_used;
        }

        if using_img {
            img_buffer = img_buffer_used;
        }

        dma2d_wait_for_transfer();
        unsafe { dma2d_start_blend(&t_buffer.buffer, &img_buffer.buffer, clamped.width()) };
    }

    dma2d_wait_for_transfer();
}

/// Renders text over image background
/// If `bg_area` is given, it is filled with its color in places where there is
/// neither icon. Positioning also depends on whether `bg_area` is provided:
/// - if it is, icons are positioned relative to the `bg_area` top left corner,
///   using respective offsets. Nothing is drawn outside the `bg_area`.
/// - if it is not, `fg` icon is positioned relative to the `bg` icons top left
///   corner using its offset and `fg` icon is positioned on the screen using
///   its offset. Nothing is drawn outside the `bg` icon.
///
/// The drawing area is coerced to even width, which is due to dma2d limitation
/// when using 4bpp
#[cfg(feature = "dma2d")]
pub fn icon_over_icon(
    bg_area: Option<Rect>,
    bg: (Icon, Offset, Color),
    fg: (Icon, Offset, Color),
    bg_color: Color,
) {
    let mut bg1 = buffers::BufferLine16bpp::get_cleared();
    let mut bg2 = buffers::BufferLine16bpp::get_cleared();
    let mut empty1 = buffers::BufferLine16bpp::get_cleared();
    let mut fg1 = buffers::BufferLine4bpp::get_cleared();
    let mut fg2 = buffers::BufferLine4bpp::get_cleared();
    let mut empty2 = buffers::BufferLine4bpp::get_cleared();

    let (icon_bg, offset_bg, color_icon_bg) = bg;
    let (icon_fg, offset_fg, color_icon_fg) = fg;

    assert!(icon_bg.toif.width() <= constant::WIDTH);
    assert_eq!(icon_bg.toif.width() % 2, 0);

    assert!(icon_fg.toif.width() <= constant::WIDTH);
    assert_eq!(icon_fg.toif.width() % 2, 0);

    let area;
    let r_bg;
    let final_offset_bg;
    if let Some(a) = bg_area {
        area = a;
        r_bg = Rect::from_top_left_and_size(a.top_left() + offset_bg, icon_bg.toif.size());
        final_offset_bg = offset_bg;
    } else {
        r_bg =
            Rect::from_top_left_and_size(Point::new(offset_bg.x, offset_bg.y), icon_bg.toif.size());
        area = r_bg;
        final_offset_bg = Offset::zero();
    }

    let r_fg = Rect::from_top_left_and_size(area.top_left() + offset_fg, icon_fg.toif.size());

    let clamped = area.clamp(constant::screen()).ensure_even_width();

    set_window(clamped);

    let mut window_bg = [0; UZLIB_WINDOW_SIZE];
    let mut ctx_bg = UzlibContext::new(icon_bg.toif.zdata(), Some(&mut window_bg));

    let mut window_fg = [0; UZLIB_WINDOW_SIZE];
    let mut ctx_fg = UzlibContext::new(icon_fg.toif.zdata(), Some(&mut window_fg));

    dma2d_setup_4bpp_over_4bpp(color_icon_bg.into(), bg_color.into(), color_icon_fg.into());

    let mut fg_i = 0;
    let mut bg_i = 0;

    for y in clamped.y0..clamped.y1 {
        let mut fg_buffer = &mut *empty2;
        let mut bg_buffer = &mut *empty1;
        let fg_buffer_used;
        let bg_buffer_used;

        if y % 2 == 0 {
            fg_buffer_used = &mut *fg1;
            bg_buffer_used = &mut *bg1;
        } else {
            fg_buffer_used = &mut *fg2;
            bg_buffer_used = &mut *bg2;
        }

        let using_fg = process_buffer(
            y,
            r_fg,
            offset_fg,
            &mut ctx_fg,
            &mut fg_buffer_used.buffer,
            &mut fg_i,
            4,
        );
        let using_bg = process_buffer(
            y,
            r_bg,
            final_offset_bg,
            &mut ctx_bg,
            &mut bg_buffer_used.buffer,
            &mut bg_i,
            4,
        );

        if using_fg {
            fg_buffer = fg_buffer_used;
        }
        if using_bg {
            bg_buffer = bg_buffer_used;
        }

        dma2d_wait_for_transfer();
        unsafe { dma2d_start_blend(&fg_buffer.buffer, &bg_buffer.buffer, clamped.width()) };
    }

    dma2d_wait_for_transfer();
}

#[cfg(not(feature = "dma2d"))]
pub fn icon_over_icon(
    bg_area: Option<Rect>,
    bg: (Icon, Offset, Color),
    fg: (Icon, Offset, Color),
    bg_color: Color,
) {
    let (icon_bg, offset_bg, color_icon_bg) = bg;
    let (icon_fg, offset_fg, color_icon_fg) = fg;

    let pos_bg = if let Some(area) = bg_area {
        rect_fill(area, bg_color);
        area.top_left() + offset_bg
    } else {
        Point::from(offset_bg)
    };

    icon_bg.draw(pos_bg, Alignment2D::TOP_LEFT, color_icon_bg, bg_color);
    icon_fg.draw(
        pos_bg + offset_fg,
        Alignment2D::TOP_LEFT,
        color_icon_fg,
        color_icon_bg,
    );
}

/// Gets a color of a pixel on `p` coordinates of rounded rectangle with corner
/// radius 2
fn rect_rounded2_get_pixel(
    p: Offset,
    size: Offset,
    colortable: [Color; 16],
    fill: bool,
    line_width: i16,
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
    fill_from: i16,
    fill_to: i16,
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

pub fn marquee(area: Rect, text: &str, offset: i16, font: Font, fg: Color, bg: Color) {
    let mut buffer = buffers::BufferText::get_cleared();

    let area = area.translate(get_offset());
    let clamped = area.clamp(constant::screen());
    set_window(clamped);

    display::text_into_buffer(text, font.into(), &mut buffer, offset);
    let tbl = get_color_table(fg, bg);

    for y in 0..clamped.height() {
        for x in 0..clamped.width() {
            let pixel = y * constant::WIDTH + x;
            let byte_idx = pixel / 2;
            if byte_idx < buffer.buffer.len() as _ {
                let data = if pixel % 2 != 0 {
                    buffer.buffer[byte_idx as usize] >> 4
                } else {
                    buffer.buffer[byte_idx as usize] & 0xF
                };
                pixeldata(tbl[data as usize]);
            } else {
                pixeldata(bg);
            }
        }
    }

    pixeldata_dirty();
}

pub fn dotted_line(start: Point, width: i16, color: Color, step: i16) {
    for x in (start.x..width).step_by(step as usize) {
        rect_fill(
            Rect::from_top_left_and_size(Point::new(x, start.y), Offset::new(1, 1)),
            color,
        );
    }
}

/// Display text left-aligned to a certain Point
pub fn text_left(baseline: Point, text: &str, font: Font, fg_color: Color, bg_color: Color) {
    display::text(
        baseline.x,
        baseline.y,
        text,
        font.into(),
        fg_color.into(),
        bg_color.into(),
    );
}

/// Display text centered around a certain Point
pub fn text_center(baseline: Point, text: &str, font: Font, fg_color: Color, bg_color: Color) {
    let w = font.text_width(text);
    display::text(
        baseline.x - w / 2,
        baseline.y,
        text,
        font.into(),
        fg_color.into(),
        bg_color.into(),
    );
}

/// Display text right-aligned to a certain Point
pub fn text_right(baseline: Point, text: &str, font: Font, fg_color: Color, bg_color: Color) {
    let w = font.text_width(text);
    display::text(
        baseline.x - w,
        baseline.y,
        text,
        font.into(),
        fg_color.into(),
        bg_color.into(),
    );
}

pub fn text_top_left(position: Point, text: &str, font: Font, fg_color: Color, bg_color: Color) {
    let h = font.text_height();
    display::text(
        position.x,
        position.y + h,
        text,
        font.into(),
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

pub fn sync() {
    display::sync();
}

pub fn refresh() {
    display::refresh();
}

pub fn get_color_table(fg_color: Color, bg_color: Color) -> [Color; 16] {
    let mut table: [Color; 16] = [Color::from_u16(0); 16];

    for (i, item) in table.iter_mut().enumerate() {
        *item = Color::lerp(bg_color, fg_color, i as f32 / 15_f32);
    }

    table
}

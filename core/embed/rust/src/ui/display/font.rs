use crate::{
    trezorhal::display,
    ui::{
        constant,
        geometry::{Offset, Point, Rect},
    },
};
use core::slice;

use super::{get_color_table, get_offset, pixeldata, set_window, Color};

/// Representation of a single glyph.
/// We use standard typographic terms. For a nice explanation, see, e.g.,
/// the FreeType docs at https://www.freetype.org/freetype2/docs/glyphs/glyphs-3.html
pub struct Glyph {
    /// Total width of the glyph itself
    pub width: i16,
    /// Total height of the glyph itself
    pub height: i16,
    /// Advance - how much to move the cursor after drawing this glyph
    pub adv: i16,
    /// Left-side horizontal bearing
    pub bearing_x: i16,
    /// Top-side vertical bearing
    pub bearing_y: i16,
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
            let width = *data.offset(0) as i16;
            let height = *data.offset(1) as i16;

            let data_bits = constant::FONT_BPP * width * height;

            let data_bytes = if data_bits % 8 == 0 {
                data_bits / 8
            } else {
                (data_bits / 8) + 1
            };

            Glyph {
                width,
                height,
                adv: *data.offset(2) as i16,
                bearing_x: *data.offset(3) as i16,
                bearing_y: *data.offset(4) as i16,
                data: slice::from_raw_parts(data.offset(5), data_bytes as usize),
            }
        }
    }

    /// Space between the right edge of the glyph and the left edge of the next
    /// bounding box.
    pub const fn right_side_bearing(&self) -> i16 {
        self.adv - self.width - self.bearing_x
    }

    pub fn print(&self, pos: Point, colortable: [Color; 16]) -> i16 {
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

    pub fn unpack_bpp1(&self, a: i16) -> u8 {
        let c_data = self.data[(a / 8) as usize];
        ((c_data >> (7 - (a % 8))) & 0x01) * 15
    }

    pub fn unpack_bpp2(&self, a: i16) -> u8 {
        let c_data = self.data[(a / 4) as usize];
        ((c_data >> (6 - (a % 4) * 2)) & 0x03) * 5
    }

    pub fn unpack_bpp4(&self, a: i16) -> u8 {
        let c_data = self.data[(a / 2) as usize];
        (c_data >> (4 - (a % 2) * 4)) & 0x0F
    }

    pub fn unpack_bpp8(&self, a: i16) -> u8 {
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

/// Font constants. Keep in sync with FONT_ definitions in
/// `extmod/modtrezorui/fonts/fonts.h`.
#[derive(Copy, Clone, PartialEq, Eq, FromPrimitive)]
#[repr(u8)]
pub enum Font {
    NORMAL = 1,
    BOLD = 2,
    MONO = 3,
    BIG = 4,
    DEMIBOLD = 5,
}

impl From<Font> for i32 {
    fn from(font: Font) -> i32 {
        -(font as i32)
    }
}

impl Font {
    pub fn text_width(self, text: &str) -> i16 {
        display::text_width(text, self.into())
    }

    /// Supports UTF8 characters
    fn get_first_glyph_from_text(self, text: &str) -> Option<Glyph> {
        text.chars().next().map(|c| self.get_glyph(c))
    }

    /// Supports UTF8 characters
    fn get_last_glyph_from_text(self, text: &str) -> Option<Glyph> {
        text.chars().next_back().map(|c| self.get_glyph(c))
    }

    /// Width of the text that is visible.
    /// Not including the spaces before the first and after the last character.
    pub fn visible_text_width(self, text: &str) -> i16 {
        if text.is_empty() {
            // No text, no width.
            return 0;
        }

        let first_char_bearing = if let Some(glyph) = self.get_first_glyph_from_text(text) {
            glyph.bearing_x
        } else {
            0
        };

        let last_char_bearing = if let Some(glyph) = self.get_last_glyph_from_text(text) {
            glyph.right_side_bearing()
        } else {
            0
        };

        // Strip leftmost and rightmost spaces/bearings/margins.
        self.text_width(text) - first_char_bearing - last_char_bearing
    }

    /// Returning the x-bearing (offset) of the first character.
    /// Useful to enforce that the text is positioned correctly (e.g. centered).
    pub fn start_x_bearing(self, text: &str) -> i16 {
        if text.is_empty() {
            return 0;
        }

        if let Some(glyph) = self.get_first_glyph_from_text(text) {
            glyph.bearing_x
        } else {
            0
        }
    }

    pub fn char_width(self, ch: char) -> i16 {
        display::char_width(ch, self.into())
    }

    pub fn text_height(self) -> i16 {
        display::text_height(self.into())
    }

    pub fn text_max_height(self) -> i16 {
        display::text_max_height(self.into())
    }

    pub fn text_baseline(self) -> i16 {
        display::text_baseline(self.into())
    }

    pub fn max_height(self) -> i16 {
        display::text_max_height(self.into())
    }

    pub fn line_height(self) -> i16 {
        constant::LINE_SPACE + self.text_height()
    }

    pub fn get_glyph(self, ch: char) -> Glyph {
        let gl_data = display::get_char_glyph(ch as u16, self.into());

        ensure!(!gl_data.is_null(), "Failed to load glyph");
        // SAFETY: Glyph::load is valid for data returned by get_char_glyph
        unsafe { Glyph::load(gl_data) }
    }

    pub fn display_text(self, text: &str, baseline: Point, fg_color: Color, bg_color: Color) {
        let colortable = get_color_table(fg_color, bg_color);
        let mut adv_total = 0;
        for c in text.chars() {
            let gly = self.get_glyph(c);
            let adv = gly.print(baseline + Offset::new(adv_total, 0), colortable);
            adv_total += adv;
        }
    }

    /// Get the length of the longest suffix from a given `text`
    /// that will fit into the area `width` pixels wide.
    pub fn longest_suffix(self, width: i16, text: &str) -> usize {
        let mut text_width = 0;
        for (chars_from_right, c) in text.chars().rev().enumerate() {
            let c_width = self.char_width(c);
            if text_width + c_width > width {
                // Another character cannot be fitted, we're done.
                return chars_from_right;
            }
            text_width += c_width;
        }

        text.len() // it fits in its entirety
    }
}

pub trait GlyphMetrics {
    fn char_width(&self, ch: char) -> i16;
    fn text_width(&self, text: &str) -> i16;
    fn line_height(&self) -> i16;
}

impl GlyphMetrics for Font {
    fn char_width(&self, ch: char) -> i16 {
        Font::char_width(*self, ch)
    }

    fn text_width(&self, text: &str) -> i16 {
        Font::text_width(*self, text)
    }

    fn line_height(&self) -> i16 {
        Font::line_height(*self)
    }
}

use spin::RwLockReadGuard;

use crate::{
    trezorhal::display::{self},
    ui::{
        constant,
        geometry::Offset,
        shape::{Bitmap, BitmapFormat},
    },
};
use core::slice;

#[cfg(feature = "translations")]
use crate::translations::flash;
#[cfg(feature = "translations")]
use crate::translations::Translations;

/// Representation of a single glyph.
/// We use standard typographic terms. For a nice explanation, see, e.g.,
/// the FreeType docs at https://www.freetype.org/freetype2/docs/glyphs/glyphs-3.html
pub struct Glyph<'a> {
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
    data: &'a [u8],
}

impl<'a> Glyph<'a> {
    /// Creates a new `Glyph` from a byte slice containing font data.
    ///
    /// Expected data format (bytes):
    /// - 0: glyph width
    /// - 1: glyph height
    /// - 2: advance width
    /// - 3: x-bearing
    /// - 4: y-bearing
    /// - 5...: bitmap data, packed according to FONT_BPP (bits per pixel)
    pub fn load(data: &'a [u8]) -> Self {
        let width = data[0] as i16;
        let height = data[1] as i16;

        let size = calculate_glyph_size(data);
        // This should check for equality but due to a previous bug in font generator,
        // some glyphs in older translation blobs might have a trailing zero byte.
        ensure!(data.len() >= size, "Invalid glyph data size");
        Glyph {
            width,
            height,
            adv: data[2] as i16,
            bearing_x: data[3] as i16,
            bearing_y: data[4] as i16,
            data: &data[5..],
        }
    }

    /// Space between the right edge of the glyph and the left edge of the next
    /// bounding box.
    pub const fn right_side_bearing(&self) -> i16 {
        self.adv - self.width - self.bearing_x
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

    pub fn bitmap(&self) -> Bitmap<'a> {
        match constant::FONT_BPP {
            1 => unwrap!(Bitmap::new(
                BitmapFormat::MONO1P,
                None,
                Offset::new(self.width, self.height),
                None,
                self.data,
            )),
            4 => unwrap!(Bitmap::new(
                BitmapFormat::MONO4,
                None,
                Offset::new(self.width, self.height),
                None,
                self.data,
            )),
            _ => unimplemented!(),
        }
    }
}

/// A provider of font glyphs and their metadata.
///
/// Manages access to font resources and handles UTF-8 character glyphs
///
/// The provider holds necessary lock for accessing translation data
/// and is typically used through the `Font::with_glyph_data` method
/// to ensure proper resource cleanup.
///
/// # Example
/// ```
/// let font = Font::NORMAL;
/// font.with_glyph_data(|data| {
///     let glyph = data.get_glyph('A');
///     // use glyph...
/// });
/// ```
pub struct GlyphData {
    font: Font,
    #[cfg(feature = "translations")]
    translations_guard: Option<RwLockReadGuard<'static, Option<Translations<'static>>>>,
}

impl GlyphData {
    fn new(font: Font) -> Self {
        #[cfg(feature = "translations")]
        let translations_guard = flash::get().ok();

        Self {
            font,
            #[cfg(feature = "translations")]
            translations_guard,
        }
    }

    pub fn get_glyph(&self, ch: char) -> Glyph<'_> {
        let ch = match ch {
            '\u{00a0}' => '\u{0020}',
            c => c,
        };
        let gl_data = self.get_glyph_data(ch as u16);

        Glyph::load(unwrap!(gl_data, "Failed to load glyph"))
    }

    fn get_glyph_data(&self, codepoint: u16) -> Option<&[u8]> {
        display::get_font_info(self.font.into()).map(|font_info| {
            if codepoint >= ' ' as u16 && codepoint < 0x7F {
                // ASCII character
                let offset = codepoint - ' ' as u16;
                unsafe {
                    let ptr = *font_info.glyph_data.offset(offset as isize);
                    self.load_glyph_from_ptr(ptr)
                }
            } else {
                #[cfg(feature = "translations")]
                {
                    if codepoint >= 0x7F {
                        // UTF8 character from embedded blob
                        if let Some(glyph) = self
                            .translations_guard
                            .as_ref()
                            .and_then(|guard| guard.as_ref())
                            .and_then(|translations| {
                                translations.get_utf8_glyph(codepoint, self.font as u16)
                            })
                        {
                            return glyph;
                        }
                    }
                }
                self.glyph_nonprintable()
            }
        })
    }

    /// Returns glyph data slice from a raw pointer by reading the header and
    /// calculating full size.
    unsafe fn load_glyph_from_ptr(&self, ptr: *const u8) -> &[u8] {
        unsafe {
            let header = slice::from_raw_parts(ptr, 2);
            let full_size = calculate_glyph_size(header);
            slice::from_raw_parts(ptr, full_size)
        }
    }

    /// Returns glyph data slize for non-printable characters.
    fn glyph_nonprintable(&self) -> &[u8] {
        display::get_font_info(self.font.into())
            .map(|font_info| unsafe { self.load_glyph_from_ptr(font_info.glyph_nonprintable) })
            .unwrap()
    }
}

fn calculate_glyph_size(header: &[u8]) -> usize {
    let width = header[0] as i16;
    let height = header[1] as i16;

    let data_bytes = match constant::FONT_BPP {
        1 => (width * height + 7) / 8, // packed bits
        2 => (width * height + 3) / 4, // packed bits
        4 => (width + 1) / 2 * height, // row aligned to bytes
        8 => width * height,
        _ => fatal_error!("Unsupported font bpp"),
    };

    5 + data_bytes as usize // header (5 bytes) + bitmap data
}

/// Font constants. Keep in sync with `font_id_t` definition in
/// `core/embed/gfx/fonts/fonts.h`.
#[derive(Copy, Clone, PartialEq, Eq, FromPrimitive)]
#[repr(u8)]
#[allow(non_camel_case_types)]
pub enum Font {
    NORMAL = 1,
    BOLD = 2,
    MONO = 3,
    BIG = 4,
    DEMIBOLD = 5,
    NORMAL_UPPER = 6,
    BOLD_UPPER = 7,
    SUB = 8,
}

impl From<Font> for i32 {
    fn from(font: Font) -> i32 {
        -(font as i32)
    }
}

impl Font {
    /// Supports UTF8 characters
    pub fn text_width(self, text: &str) -> i16 {
        self.with_glyph_data(|data| {
            text.chars().fold(0, |acc, c| {
                let char_width = data.get_glyph(c).adv;
                acc + char_width
            })
        })
    }

    /// Width of the text that is visible.
    /// Not including the spaces before the first and after the last character.
    pub fn visible_text_width(self, text: &str) -> i16 {
        if text.is_empty() {
            // No text, no width.
            return 0;
        }

        let (first_char_bearing, last_char_bearing) = self.with_glyph_data(|data| {
            let first = text
                .chars()
                .next()
                .map_or(0, |c| data.get_glyph(c).bearing_x);
            let last = text
                .chars()
                .next_back()
                .map_or(0, |c| data.get_glyph(c).right_side_bearing());
            (first, last)
        });

        // Strip leftmost and rightmost spaces/bearings/margins.
        self.text_width(text) - first_char_bearing - last_char_bearing
    }

    /// Calculates the height of visible text.
    ///
    /// It determines this height by finding the highest
    /// pixel above the baseline and the lowest pixel below the baseline among
    /// the glyphs representing the characters in the provided text.
    pub fn visible_text_height(self, text: &str) -> i16 {
        let (mut ascent, mut descent) = (0, 0);
        self.with_glyph_data(|data| {
            for c in text.chars() {
                let glyph = data.get_glyph(c);
                ascent = ascent.max(glyph.bearing_y);
                descent = descent.max(glyph.height - glyph.bearing_y);
            }
        });
        ascent + descent
    }

    /// Calculates the height of text containing both uppercase
    /// and lowercase characters.
    ///
    /// This function computes the height of a string containing both
    /// uppercase and lowercase characters of the given font.
    pub fn allcase_text_height(self) -> i16 {
        self.visible_text_height("Ay")
    }

    /// Returning the x-bearing (offset) of the first character.
    /// Useful to enforce that the text is positioned correctly (e.g. centered).
    pub fn start_x_bearing(self, text: &str) -> i16 {
        if text.is_empty() {
            return 0;
        }

        text.chars().next().map_or(0, |c| {
            self.with_glyph_data(|data| data.get_glyph(c).bearing_x)
        })
    }

    pub fn char_width(self, ch: char) -> i16 {
        self.with_glyph_data(|data| data.get_glyph(ch).adv)
    }

    pub fn text_height(self) -> i16 {
        unwrap!(display::get_font_info(self.into())).height as i16
    }

    pub fn text_max_height(self) -> i16 {
        unwrap!(display::get_font_info(self.into())).max_height as i16
    }

    pub fn text_baseline(self) -> i16 {
        unwrap!(display::get_font_info(self.into())).baseline as i16
    }

    pub fn line_height(self) -> i16 {
        constant::LINE_SPACE + self.text_height()
    }

    /// Helper functions for **horizontal** text centering.
    ///
    /// The `text` is centered between `start` and `end`.
    ///
    /// Returns x-coordinate of the centered text start (including left
    /// bearing).
    pub fn horz_center(&self, start: i16, end: i16, text: &str) -> i16 {
        (start + end - self.visible_text_width(text)) / 2 - self.start_x_bearing(text)
    }

    /// Helper functions for **vertical** text centering.
    ///
    /// The `text` is centered between `start` and `end`.
    ///
    /// Returns y-coordinate of the centered text baseline.
    pub fn vert_center(&self, start: i16, end: i16, text: &str) -> i16 {
        (start + end + self.visible_text_height(text)) / 2
    }

    /// Safely manages temporary access to glyph data without risking
    /// translation lock deadlocks. See `GlyphData` for more details.
    pub fn with_glyph_data<T, F>(&self, f: F) -> T
    where
        F: FnOnce(&GlyphData) -> T,
    {
        // Create a new GlyphData instance that will be dropped at the end of this
        // function, releasing any translations lock
        let glyph_data = GlyphData::new(*self);
        f(&glyph_data)
    }

    /// Get the longest prefix of a given `text` (breaking at word boundaries)
    /// that will fit into the area `width` pixels wide.
    pub fn longest_prefix(self, width: i16, text: &str) -> &str {
        let mut prev_word_boundary = 0;
        let mut text_width = 0;
        self.with_glyph_data(|data| {
            for (i, c) in text.char_indices() {
                let char_width = data.get_glyph(c).adv;
                let c_width = char_width;
                if text_width + c_width > width {
                    // Another character would not fit => split at the previous word boundary
                    return &text[0..prev_word_boundary];
                }
                if c == ' ' {
                    prev_word_boundary = i;
                }
                text_width += c_width;
            }
            text // the whole text fits
        })
    }

    /// Get the length of the longest suffix from a given `text`
    /// that will fit into the area `width` pixels wide.
    pub fn longest_suffix(self, width: i16, text: &str) -> usize {
        let mut text_width = 0;

        self.with_glyph_data(|data| {
            for (chars_from_right, c) in text.chars().rev().enumerate() {
                let char_width = data.get_glyph(c).adv;
                if text_width + char_width > width {
                    // Another character cannot be fitted, we're done.
                    return chars_from_right;
                }
                text_width += char_width;
            }
            text.len() // it fits in its entirety
        })
    }

    pub fn visible_text_height_ex(&self, text: &str) -> (i16, i16) {
        let (mut ascent, mut descent) = (0, 0);
        self.with_glyph_data(|data| {
            for c in text.chars() {
                let glyph = data.get_glyph(c);
                ascent = ascent.max(glyph.bearing_y);
                descent = descent.max(glyph.height - glyph.bearing_y);
            }
            (ascent, descent)
        })
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

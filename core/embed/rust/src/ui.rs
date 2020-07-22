use core::{
    convert::{TryFrom, TryInto},
    ops::Range,
};

use crate::error::Error;
use crate::micropython::{
    buffer::Buffer,
    iter::{Iter, IterBuf},
    map::Map,
    obj::Obj,
    qstr::Qstr,
};
use crate::trezorhal::display;

/// A point in 2D space defined by the the `x` and `y` coordinate.
#[derive(Copy, Clone, PartialEq, Eq)]
struct Point {
    x: i32,
    y: i32,
}

/// A rectangle in 2D space defined by the top-left point `x0`,`y0` and the
/// bottom-right point `x1`,`y1`.
#[derive(Copy, Clone, PartialEq, Eq)]
struct Rect {
    x0: i32,
    y0: i32,
    x1: i32,
    y1: i32,
}

/// Visual instructions for layout out and rendering of a `RichText` block.
struct Style {
    /// Foreground (text) color. Can be overriden by `Op::SetFg` opcode.
    fg: u16,
    /// Background color.
    bg: u16,
    /// Font descriptor. Can be overridden by `Op::SetFont` opcode. Specific
    /// values depends on used `Shaper` impl.
    font: i32,
    /// Whether to allow line breaks in the middle of the words, or only at
    /// whitespace.
    break_words: bool,
    /// Whether to automatically insert new lines after each `Op`. If `false`,
    /// a space is used instead.
    insert_new_lines: bool,
    /// Whether to draw ellipsis to indicate text can no longer fit in the given
    /// bounds.
    render_page_overflow: bool,
}

/// A structure describing a block of rich text.
struct RichText {
    /// An iterable object yielding items decodable into the `Op` enum.
    ops: Obj,
    /// Specifies the first element of `ops` which should be considered.
    op_offset: usize,
    /// Specifies the first character of the item indicated in `op_offset`
    /// which should be considered.
    char_offset: usize,
    /// Layout style, specifying the visual and layout parameters of the text.
    style: Style,
    /// A bounding box restricting the layout and rendering.
    bounds: Rect,
}

enum Op {
    /// Set current text color.
    SetFg(u16),
    /// Set currently used font.
    SetFont(i32),
    /// Render text with current color and font, breaking lines according to
    /// `Style`.
    Render(Buffer),
}

const LINE_HEIGHT: i32 = 26;
const LINE_HEIGHT_HALF: i32 = 13;

impl RichText {
    fn render(&mut self) -> Result<(), Error> {
        // Current position of the drawing cursor in the global coordinate space. We
        // start drawing in the top-left corner of our bounds.
        let mut cursor = Point {
            x: self.bounds.x0,
            y: self.bounds.y0 + LINE_HEIGHT, // Advance to the baseline.
        };
        // Iterate and interpret the `ops`. We're skipping all `Op::Render` bellow
        // `op_offset`, but the styling ops still need to be applied.
        let mut ops_buf = IterBuf::new();
        let ops = Iter::try_from_obj_with_buf(self.ops, &mut ops_buf)?;
        for (i, op) in ops.into_iter().enumerate() {
            match Op::try_from(op)? {
                Op::SetFg(fg) => {
                    self.style.fg = fg;
                }
                Op::SetFont(font) => {
                    self.style.font = font;
                }
                Op::Render(buffer) => {
                    if i < self.op_offset {
                        continue;
                    }
                    // If this is the first text op, seek to the correct starting char.
                    let text = if i == self.op_offset {
                        &buffer[self.char_offset..]
                    } else {
                        &buffer
                    };
                    render_text(text, &self.style, &self.bounds, &mut cursor, &mut TrezorHal)?;
                }
            }
        }
        Ok(())
    }
}

struct Span {
    /// Slice of the input text this span is laying out.
    range: Range<usize>,
    /// By how much to offset the cursor horizontally after drawing.
    advance_x: i32,
    /// By how much to offset the cursor vertically after drawing. If bigger
    /// than zero, it means we are breaking the line.
    advance_y: i32,
    /// If we are breaking the line, should we draw a hyphen right after this
    /// span to indicate a word-break?
    draw_hyphen_before_line_break: bool,
    /// Should we skip the first leading whitespace character before fitting the
    /// next span?
    skip_next_leading_whitespace: bool,
}

/// Encapsulation of the underlying text API primitives.
trait Shaper {
    fn render_text(&mut self, x: i32, y: i32, text: &[u8], font: i32, fg: u16, bg: u16);
    fn text_width(&mut self, text: &[u8], font: i32) -> i32;
}

struct TrezorHal;

impl Shaper for TrezorHal {
    fn render_text(&mut self, x: i32, y: i32, text: &[u8], font: i32, fg: u16, bg: u16) {
        display::text(x, y, text, font, fg, bg);
    }

    fn text_width(&mut self, text: &[u8], font: i32) -> i32 {
        display::text_width(text, font)
    }
}

const ASCII_LF: u8 = 10;
const ASCII_CR: u8 = 13;
const ASCII_SPACE: u8 = 32;
const ASCII_HYPHEN: u8 = 45;
const HYPHEN_FONT: i32 = -2; // FONT_BOLD
const ELLIPSIS_FONT: i32 = -1; // FONT_NORMAL

fn render_text(
    text: &[u8],
    style: &Style,
    bounds: &Rect,
    cursor: &mut Point,
    shaper: &mut impl Shaper,
) -> Result<(), Error> {
    let mut skip_leading_whitespace = false;
    let mut remaining_text = text;

    while !remaining_text.is_empty() {
        let span = find_fitting_span(
            remaining_text,
            bounds.x1 - cursor.x,
            style.font,
            style.break_words,
            skip_leading_whitespace,
            shaper,
        );

        // Render the span at the cursor position.
        shaper.render_text(
            cursor.x,
            cursor.y,
            &remaining_text[span.range.start..span.range.end],
            style.font,
            style.fg,
            style.bg,
        );

        // Advance the cursor horizontally.
        cursor.x += span.advance_x;

        if span.advance_y > 0 {
            // We're advacing to the next line, so we need to check the amount of vertical
            // space we have left. If we would be overflowing it, we might want to draw a
            // symbol indicating that more content is available. Because we do not really
            // check if the symbol fits on the horizontal axis, we might be painting out of
            // the horizontal bounds. This is intentional.
            if style.render_page_overflow && cursor.y + span.advance_y > bounds.y1 {
                render_page_overflow(cursor, style, shaper);
                // We're out of both horizontal and vertical space, quit.
                break;
            }
            // We have space to advance to the next line, check if we should be drawing a
            // hyphen at this point.
            if span.draw_hyphen_before_line_break {
                render_hyphen(cursor, style, shaper);
            }
            // Advance the cursor to the beginning of the next line.
            cursor.x = bounds.x0;
            cursor.y += span.advance_y;
        }

        // Continue with the rest of the text.
        remaining_text = &remaining_text[span.range.end..];
        skip_leading_whitespace = span.skip_next_leading_whitespace;
    }

    // After each printable text item, we insert either a new line or a space.
    let text_is_all_whitespace = text.iter().all(|&ch| is_whitespace(ch));
    if !text_is_all_whitespace {
        if style.insert_new_lines {
            cursor.x = bounds.x0;
            cursor.y += LINE_HEIGHT;
        } else {
            cursor.x += shaper.text_width(&[ASCII_SPACE], style.font);
        }
    }

    Ok(())
}

fn render_page_overflow(pos: &Point, style: &Style, shaper: &mut impl Shaper) {
    shaper.render_text(
        pos.x,
        pos.y,
        "...".as_bytes(),
        ELLIPSIS_FONT,
        style.fg,
        style.bg,
    );
}

fn render_hyphen(pos: &Point, style: &Style, shaper: &mut impl Shaper) {
    shaper.render_text(
        pos.x,
        pos.y,
        &[ASCII_HYPHEN],
        HYPHEN_FONT,
        style.fg,
        style.bg,
    );
}

fn find_fitting_span(
    text: &[u8],
    max_width: i32,
    font: i32,
    break_words: bool,
    skip_leading_whitespace: bool,
    shaper: &mut impl Shaper,
) -> Span {
    let hyphen_width = shaper.text_width(&[ASCII_HYPHEN], HYPHEN_FONT);

    // The span we return in case a line has to break. We mutate it in the possible
    // break points, and its initial value is returned in case no text at all is
    // fitting the constraints: empty range, zero width, full line break.
    let mut line = Span {
        range: 0..0,
        advance_x: 0,
        advance_y: LINE_HEIGHT,
        draw_hyphen_before_line_break: false,
        skip_next_leading_whitespace: false,
    };

    let mut span_width = 0;
    let mut skipping_whitespace = skip_leading_whitespace;

    for i in 0..text.len() {
        let ch = text[i];

        // Usually, spans start at the beginning of `text`, with one exception: after we
        // break the text before a whitespace, we need to skip this whitespace when
        // fitting the next span.
        if skipping_whitespace {
            if is_whitespace(ch) {
                continue;
            } else {
                line.range.start = i;
                skipping_whitespace = false;
            }
        }

        let char_width = shaper.text_width(&[ch], font);

        // Consider if we could be breaking this line at this position.
        if is_whitespace(ch) {
            // Break before the whitespace, without hyphen.
            line.range.end = i;
            line.advance_x = span_width;
            line.draw_hyphen_before_line_break = false;
            line.skip_next_leading_whitespace = true;
            if ch == ASCII_CR {
                // We'll be breaking the line, but advancing the cursor only by a half of the
                // regular line height.
                line.advance_y = LINE_HEIGHT_HALF;
            }
            if ch == ASCII_LF || ch == ASCII_CR {
                // End of line, break immediately.
                return line;
            }
        } else if break_words && span_width + char_width + hyphen_width < max_width {
            // Break after this character, append hyphen.
            line.range.end = i + 1;
            line.advance_x = span_width + char_width;
            line.draw_hyphen_before_line_break = true;
            line.skip_next_leading_whitespace = false;
        }

        if span_width + char_width > max_width {
            // Return the last breakpoint.
            return line;
        }

        span_width += char_width;
    }

    // The whole text is fitting.
    Span {
        range: line.range.start..text.len(),
        advance_x: span_width,
        advance_y: 0,
        draw_hyphen_before_line_break: false,
        skip_next_leading_whitespace: false,
    }
}

fn is_whitespace(ch: u8) -> bool {
    ch == ASCII_SPACE || ch == ASCII_LF || ch == ASCII_CR
}

impl TryFrom<&Map> for Rect {
    type Error = Error;

    fn try_from(map: &Map) -> Result<Self, Self::Error> {
        Ok(Self {
            x0: map.get_qstr(Qstr::MP_QSTR_x0)?.try_into()?,
            y0: map.get_qstr(Qstr::MP_QSTR_y0)?.try_into()?,
            x1: map.get_qstr(Qstr::MP_QSTR_x1)?.try_into()?,
            y1: map.get_qstr(Qstr::MP_QSTR_y1)?.try_into()?,
        })
    }
}

impl TryFrom<&Map> for Style {
    type Error = Error;

    fn try_from(map: &Map) -> Result<Self, Self::Error> {
        Ok(Self {
            fg: map.get_qstr(Qstr::MP_QSTR_fg)?.try_into()?,
            bg: map.get_qstr(Qstr::MP_QSTR_bg)?.try_into()?,
            font: map.get_qstr(Qstr::MP_QSTR_font)?.try_into()?,
            break_words: map.get_qstr(Qstr::MP_QSTR_break_words)?.try_into()?,
            insert_new_lines: map.get_qstr(Qstr::MP_QSTR_insert_new_lines)?.try_into()?,
            render_page_overflow: map
                .get_qstr(Qstr::MP_QSTR_render_page_overflow)?
                .try_into()?,
        })
    }
}

impl TryFrom<Obj> for Op {
    type Error = Error;

    fn try_from(obj: Obj) -> Result<Self, Self::Error> {
        // TODO: Match on `obj` type directly, instead of trying to match the variants
        // one by one.
        if let Ok(buf) = Buffer::try_from(obj) {
            // Text buffer.
            Ok(Self::Render(buf))
        } else if let Ok(val) = i32::try_from(obj) {
            // Either a font or the foreground color.
            if val < 0 {
                Ok(Self::SetFont(val))
            } else {
                Ok(Self::SetFg(val.try_into().map_err(|_| Error::OutOfRange)?))
            }
        } else {
            Err(Error::Missing)
        }
    }
}

impl TryFrom<&Map> for RichText {
    type Error = Error;

    fn try_from(map: &Map) -> Result<Self, Self::Error> {
        Ok(Self {
            ops: map.get_qstr(Qstr::MP_QSTR_items)?,
            op_offset: map.get_qstr(Qstr::MP_QSTR_item_offset)?.try_into()?,
            char_offset: map.get_qstr(Qstr::MP_QSTR_char_offset)?.try_into()?,
            style: map.try_into()?,
            bounds: map.try_into()?,
        })
    }
}

#[no_mangle]
pub extern "C" fn ui_render_rich_text(kw: *const Map) -> Obj {
    try_with_kw(kw, |kw| {
        let mut rich_text = RichText::try_from(kw)?;
        rich_text.render()?;
        Ok(Obj::const_true())
    })
}

fn try_with_kw(kw: *const Map, func: impl FnOnce(&Map) -> Result<Obj, Error>) -> Obj {
    unsafe { kw.as_ref() }
        .and_then(|kw| func(kw).ok())
        .unwrap_or(Obj::const_none())
}

use core::{
    convert::{TryFrom, TryInto},
    ops::Range,
};

use crate::{
    error::Error,
    micropython::{
        buffer::Buffer,
        iter::{Iter, IterBuf},
        map::Map,
        obj::Obj,
        qstr::Qstr,
    },
    ui::{
        display,
        math::{Color, Point, Rect},
        theme,
    },
    util,
};

/// A structure describing a block of rich text.
pub struct Text {
    /// An iterable object yielding items decodable into the `Op` enum.
    ops: Obj,
    /// Specifies the first element of `ops` which should be considered.
    op_offset: usize,
    /// Specifies the first character of the item indicated in `op_offset`
    /// which should be considered.
    char_offset: usize,
    /// Layout style, specifying the visual and layout parameters of the text.
    style: TextStyle,
    /// A bounding box restricting the layout and rendering.
    bounds: Rect,
    /// Optional callable object overriding the `render_text` fn of shaping.
    render_text_fn: Option<Obj>,
    /// Optional callable object. If set, it is called when the rendering cannot
    /// longer fit in the given `bounds`, and index of the current `op`,
    /// together with the char offset is given as arguments. Rendering will also
    /// not end in such case, cursor is reset to the beginning and next `op` (or
    /// part of it) is processed, as if rendering the next page.
    page_end_fn: Option<Obj>,
}

/// Visual instructions for layout out and rendering of a `Text` block.
pub struct TextStyle {
    /// Foreground (text) color. Can be overriden by `Op::SetFg` opcode.
    fg: Color,
    /// Background color.
    bg: Color,
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

enum Op {
    /// Set current text color.
    SetFg(Color),
    /// Set currently used font.
    SetFont(i32),
    /// Render text with current color and font, breaking lines according to
    /// `Style`.
    Render(Buffer),
}

impl Text {
    fn render(&mut self) -> Result<(), Error> {
        // Construct a `Shaper` impl with overridable `render_text` fn.
        let mut shaper = Override {
            inner: TrezorHal,
            render_text_fn: self.render_text_fn,
        };

        // Current position of the drawing cursor in the global coordinate space. We
        // start drawing in the top-left corner of our bounds.
        let initial_cursor = Point {
            x: self.bounds.x0,
            y: self.bounds.y0 + shaper.line_height(), // Advance to the baseline.
        };
        let mut cursor = initial_cursor;

        // Iterate and interpret the `ops`. We're skipping all `Op::Render` bellow
        // `op_offset`, but the styling ops still need to be applied.
        let mut ops_buf = IterBuf::new();
        let ops = Iter::try_from_obj_with_buf(self.ops, &mut ops_buf)?;
        for (op_index, op) in ops.into_iter().enumerate() {
            match Op::try_from(op)? {
                Op::SetFg(fg) => {
                    self.style.fg = fg;
                }
                Op::SetFont(font) => {
                    self.style.font = font;
                }
                Op::Render(buffer) => {
                    if op_index < self.op_offset {
                        continue;
                    }
                    // If this is the first text op, seek to the correct starting char.
                    let text = if op_index == self.op_offset {
                        &buffer[self.char_offset..]
                    } else {
                        &buffer
                    };
                    let cont = render_text(
                        text,
                        &self.style,
                        &self.bounds,
                        &mut cursor,
                        &mut shaper,
                        |processed| {
                            // If we have a `page_end_fn`, call it to report a page end, reset the
                            // cursor to the beginning and continue, as if rendering the next page.
                            // If not, quit, because we're out of bounds.
                            if let Some(obj) = self.page_end_fn {
                                let char_offset = if op_index == self.op_offset {
                                    self.char_offset + processed
                                } else {
                                    processed
                                };
                                call_page_end_obj(obj, op_index, char_offset);
                                Some(initial_cursor)
                            } else {
                                None
                            }
                        },
                    )?;
                    if let Continuation::Break = cont {
                        break;
                    }
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
    /// How many chars from the input text should we skip before fitting the
    /// next span?
    skip_next_chars: usize,
}

/// Encapsulation of the underlying text API primitives.
trait Shaper {
    fn render_text(&mut self, baseline: Point, text: &[u8], font: i32, fg: Color, bg: Color);
    fn text_width(&mut self, text: &[u8], font: i32) -> i32;
    fn line_height(&mut self) -> i32;
}

struct TrezorHal;

impl Shaper for TrezorHal {
    fn render_text(&mut self, baseline: Point, text: &[u8], font: i32, fg: Color, bg: Color) {
        display::text(baseline, text, font, fg, bg);
    }

    fn text_width(&mut self, text: &[u8], font: i32) -> i32 {
        display::text_width(text, font)
    }

    fn line_height(&mut self) -> i32 {
        display::line_height()
    }
}

struct Override<T: Shaper> {
    inner: T,
    render_text_fn: Option<Obj>,
}

impl<T: Shaper> Shaper for Override<T> {
    fn render_text(&mut self, baseline: Point, text: &[u8], font: i32, fg: Color, bg: Color) {
        match self.render_text_fn {
            Some(obj) if obj != Obj::const_none() => {
                call_render_text_obj(obj, baseline, text, font, fg, bg)
            }
            _ => self.inner.render_text(baseline, text, font, fg, bg),
        }
    }

    fn text_width(&mut self, text: &[u8], font: i32) -> i32 {
        self.inner.text_width(text, font)
    }

    fn line_height(&mut self) -> i32 {
        self.inner.line_height()
    }
}

fn call_render_text_obj(
    render_text: Obj,
    baseline: Point,
    text: &[u8],
    font: i32,
    fg: Color,
    bg: Color,
) {
    let args = [
        baseline.x.try_into().unwrap(),
        baseline.y.try_into().unwrap(),
        text.try_into().unwrap(),
        font.try_into().unwrap(),
        fg.to_u16().try_into().unwrap(),
        bg.to_u16().try_into().unwrap(),
    ];
    render_text.call_with_n_args(&args);
}

fn call_page_end_obj(page_end: Obj, op_offset: usize, char_offset: usize) {
    let args = [
        op_offset.try_into().unwrap(),
        char_offset.try_into().unwrap(),
    ];
    page_end.call_with_n_args(&args);
}

const ASCII_LF: u8 = 10;
const ASCII_CR: u8 = 13;
const ASCII_SPACE: u8 = 32;
const ASCII_HYPHEN: u8 = 45;
const HYPHEN_FONT: i32 = theme::FONT_BOLD;
const HYPHEN_COLOR: Color = theme::GREY_LIGHT;
const ELLIPSIS_FONT: i32 = theme::FONT_BOLD;
const ELLIPSIS_COLOR: Color = theme::GREY_LIGHT;

enum Continuation {
    Continue,
    Break,
}

fn render_text(
    text: &[u8],
    style: &TextStyle,
    bounds: &Rect,
    cursor: &mut Point,
    shaper: &mut impl Shaper,
    page_end_fn: impl Fn(usize) -> Option<Point>,
) -> Result<Continuation, Error> {
    let mut remaining_text = text;

    while !remaining_text.is_empty() {
        let span = find_fitting_span(
            remaining_text,
            bounds.x1 - cursor.x,
            style.font,
            style.break_words,
            shaper,
        );

        // Render the span at the cursor position.
        shaper.render_text(
            *cursor,
            &remaining_text[span.range.start..span.range.end],
            style.font,
            style.fg,
            style.bg,
        );

        // Continue with the rest of the text.
        remaining_text = &remaining_text[span.range.end + span.skip_next_chars..];

        // Advance the cursor horizontally.
        cursor.x += span.advance_x;

        if span.advance_y > 0 {
            // We're advacing to the next line.

            // Check if we should be drawing a hyphen at this point.
            if span.draw_hyphen_before_line_break {
                render_hyphen(*cursor, style, shaper);
            }
            // Check the amount of vertical space we have left.
            if cursor.y + span.advance_y > bounds.y1 {
                if !remaining_text.is_empty() {
                    // Draw ellipsis to indicate more content is available, but only if we haven't
                    // already drawn a hyphen.
                    if style.render_page_overflow && !span.draw_hyphen_before_line_break {
                        render_page_overflow(*cursor, style, shaper);
                    }
                    // Count how many chars we have processed out of `text` and call `page_end_fn`.
                    // If it returns the next cursor, move to it and continue as if nothing
                    // happened.
                    let processed = text.len() - remaining_text.len();
                    if let Some(new_cursor) = page_end_fn(processed) {
                        *cursor = new_cursor;
                        continue;
                    }
                }
                // Quit, there is not enough space for a line break.
                return Ok(Continuation::Break);
            }
            // Advance the cursor to the beginning of the next line.
            cursor.x = bounds.x0;
            cursor.y += span.advance_y;
        }
    }

    // After each text item, we insert either a new line or a space.
    if text != "\n".as_bytes() && text != "\r".as_bytes() {
        if style.insert_new_lines {
            cursor.x = bounds.x0;
            cursor.y += shaper.line_height();
        } else {
            cursor.x += shaper.text_width(&[ASCII_SPACE], style.font);
        }
    }

    Ok(Continuation::Continue)
}

fn render_page_overflow(pos: Point, style: &TextStyle, shaper: &mut impl Shaper) {
    shaper.render_text(
        pos,
        "...".as_bytes(),
        ELLIPSIS_FONT,
        ELLIPSIS_COLOR,
        style.bg,
    );
}

fn render_hyphen(pos: Point, style: &TextStyle, shaper: &mut impl Shaper) {
    shaper.render_text(pos, &[ASCII_HYPHEN], HYPHEN_FONT, HYPHEN_COLOR, style.bg);
}

fn find_fitting_span(
    text: &[u8],
    max_width: i32,
    font: i32,
    break_words: bool,
    shaper: &mut impl Shaper,
) -> Span {
    let hyphen_width = shaper.text_width(&[ASCII_HYPHEN], HYPHEN_FONT);

    // The span we return in case a line has to break. We mutate it in the possible
    // break points, and its initial value is returned in case no text at all is
    // fitting the constraints: empty range, zero width, full line break.
    let mut line = Span {
        range: 0..0,
        advance_x: 0,
        advance_y: shaper.line_height(),
        draw_hyphen_before_line_break: false,
        skip_next_chars: 0,
    };

    let mut span_width = 0;
    let mut found_any_whitespace = false;

    for i in 0..text.len() {
        let ch = text[i];

        let char_width = shaper.text_width(&[ch], font);

        // Consider if we could be breaking this line at this position.
        if is_whitespace(ch) {
            // Break before the whitespace, without hyphen.
            line.range.end = i;
            line.advance_x = span_width;
            line.draw_hyphen_before_line_break = false;
            line.skip_next_chars = 1;
            if ch == ASCII_CR {
                // We'll be breaking the line, but advancing the cursor only by a half of the
                // regular line height.
                line.advance_y = shaper.line_height() / 2;
            }
            if ch == ASCII_LF || ch == ASCII_CR {
                // End of line, break immediately.
                return line;
            }
            found_any_whitespace = true;
        } else if span_width + char_width > max_width {
            // Return the last breakpoint.
            return line;
        } else {
            let have_space_for_break = span_width + char_width + hyphen_width <= max_width;
            let can_break_word = break_words || !found_any_whitespace;
            if have_space_for_break && can_break_word {
                // Break after this character, append hyphen.
                line.range.end = i + 1;
                line.advance_x = span_width + char_width;
                line.draw_hyphen_before_line_break = true;
                line.skip_next_chars = 0;
            }
        }

        span_width += char_width;
    }

    // The whole text is fitting.
    Span {
        range: line.range.start..text.len(),
        advance_x: span_width,
        advance_y: 0,
        draw_hyphen_before_line_break: false,
        skip_next_chars: 0,
    }
}

fn is_whitespace(ch: u8) -> bool {
    ch == ASCII_SPACE || ch == ASCII_LF || ch == ASCII_CR
}

impl TryFrom<&Map> for TextStyle {
    type Error = Error;

    fn try_from(map: &Map) -> Result<Self, Self::Error> {
        Ok(Self {
            fg: Color::from_u16(map.get(Qstr::MP_QSTR_fg)?.try_into()?),
            bg: Color::from_u16(map.get(Qstr::MP_QSTR_bg)?.try_into()?),
            font: map.get(Qstr::MP_QSTR_font)?.try_into()?,
            break_words: map.get(Qstr::MP_QSTR_break_words)?.try_into()?,
            insert_new_lines: map.get(Qstr::MP_QSTR_insert_new_lines)?.try_into()?,
            render_page_overflow: map.get(Qstr::MP_QSTR_render_page_overflow)?.try_into()?,
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
                let color = Color::from_u16(val.try_into()?);
                Ok(Self::SetFg(color))
            }
        } else {
            Err(Error::InvalidType)
        }
    }
}

impl TryFrom<&Map> for Text {
    type Error = Error;

    fn try_from(map: &Map) -> Result<Self, Self::Error> {
        Ok(Self {
            ops: map.get(Qstr::MP_QSTR_items)?,
            op_offset: map.get(Qstr::MP_QSTR_item_offset)?.try_into()?,
            char_offset: map.get(Qstr::MP_QSTR_char_offset)?.try_into()?,
            style: map.try_into()?,
            bounds: map.try_into()?,
            render_text_fn: map.get(Qstr::MP_QSTR_render_text_fn).ok(),
            page_end_fn: map.get(Qstr::MP_QSTR_page_end_fn).ok(),
        })
    }
}

#[no_mangle]
pub extern "C" fn ui_render_rich_text(kwargs: *const Map) -> Obj {
    util::try_with_kwargs(kwargs, |kwargs| {
        let mut rich_text = Text::try_from(kwargs)?;
        rich_text.render()?;
        Ok(Obj::const_true())
    })
}

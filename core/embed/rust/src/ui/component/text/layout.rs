use super::iter::GlyphMetrics;
use crate::ui::{
    display,
    display::{Color, Font},
    geometry::{Offset, Point, Rect},
};

#[derive(Copy, Clone)]
pub enum LineBreaking {
    /// Break line only at whitespace, if possible. If we don't find any
    /// whitespace, break words.
    BreakAtWhitespace,
    /// Break words, adding a hyphen before the line-break. Does not use any
    /// smart algorithm, just char-by-char.
    BreakWordsAndInsertHyphen,
}

#[derive(Copy, Clone)]
pub enum PageBreaking {
    /// Stop after hitting the bottom-right edge of the bounds.
    Cut,
    /// Before stopping at the bottom-right edge, insert ellipsis to signify
    /// more content is available, but only if no hyphen has been inserted yet.
    CutAndInsertEllipsis,
}

/// Visual instructions for laying out a formatted block of text.
#[derive(Copy, Clone)]
pub struct TextLayout {
    /// Bounding box restricting the layout dimensions.
    pub bounds: Rect,

    /// Additional space before beginning of text, can be negative to shift text
    /// upwards.
    pub padding_top: i32,
    /// Additional space between end of text and bottom of bounding box, can be
    /// negative.
    pub padding_bottom: i32,

    /// Background color.
    pub background_color: Color,
    /// Text color. Can be overridden by `Op::Color`.
    pub text_color: Color,
    /// Text font ID. Can be overridden by `Op::Font`.
    pub text_font: Font,

    /// Specifies which line-breaking strategy to use.
    pub line_breaking: LineBreaking,
    /// Font used for drawing the word-breaking hyphen.
    pub hyphen_font: Font,
    /// Foreground color used for drawing the hyphen.
    pub hyphen_color: Color,

    /// Specifies what to do at the end of the page.
    pub page_breaking: PageBreaking,
    /// Font used for drawing the ellipsis.
    pub ellipsis_font: Font,
    /// Foreground color used for drawing the ellipsis.
    pub ellipsis_color: Color,

    /// Font used to format `{normal}`.
    pub normal_font: Font,
    /// Font used to format `{medium}`.
    pub medium_font: Font,
    /// Font used to format `{bold}`.
    pub bold_font: Font,
    /// Font used to format `{mono}`.
    pub mono_font: Font,
}

pub trait DefaultTextTheme {
    const BACKGROUND_COLOR: Color;
    const TEXT_FONT: Font;
    const TEXT_COLOR: Color;
    const HYPHEN_FONT: Font;
    const HYPHEN_COLOR: Color;
    const ELLIPSIS_FONT: Font;
    const ELLIPSIS_COLOR: Color;
    const NORMAL_FONT: Font;
    const MEDIUM_FONT: Font;
    const BOLD_FONT: Font;
    const MONO_FONT: Font;
}

impl TextLayout {
    /// Create a new text layout, with empty size and default text parameters
    /// filled from `T`.
    pub fn new<T: DefaultTextTheme>() -> Self {
        Self {
            bounds: Rect::zero(),
            padding_top: 0,
            padding_bottom: 0,
            background_color: T::BACKGROUND_COLOR,
            text_color: T::TEXT_COLOR,
            text_font: T::TEXT_FONT,
            line_breaking: LineBreaking::BreakAtWhitespace,
            hyphen_font: T::HYPHEN_FONT,
            hyphen_color: T::HYPHEN_COLOR,
            page_breaking: PageBreaking::CutAndInsertEllipsis,
            ellipsis_font: T::ELLIPSIS_FONT,
            ellipsis_color: T::ELLIPSIS_COLOR,
            normal_font: T::NORMAL_FONT,
            medium_font: T::MEDIUM_FONT,
            bold_font: T::BOLD_FONT,
            mono_font: T::MONO_FONT,
        }
    }

    pub fn with_bounds(mut self, bounds: Rect) -> Self {
        self.bounds = bounds;
        self
    }

    pub fn initial_cursor(&self) -> Point {
        self.bounds.top_left() + Offset::y(self.text_font.text_height() + self.padding_top)
    }

    pub fn fit_text(&self, text: &str) -> LayoutFit {
        self.layout_text(text, &mut self.initial_cursor(), &mut TextNoOp)
    }

    pub fn render_text(&self, text: &str) {
        self.layout_text(text, &mut self.initial_cursor(), &mut TextRenderer);
    }

    pub fn layout_ops<'o>(
        mut self,
        ops: &mut dyn Iterator<Item = Op<'o>>,
        cursor: &mut Point,
        sink: &mut dyn LayoutSink,
    ) -> LayoutFit {
        let init_cursor = *cursor;
        let mut total_processed_chars = 0;

        for op in ops {
            match op {
                Op::Color(color) => {
                    self.text_color = color;
                }
                Op::Font(font) => {
                    self.text_font = font;
                }
                Op::Text(text) => match self.layout_text(text, cursor, sink) {
                    LayoutFit::Fitting {
                        processed_chars, ..
                    } => {
                        total_processed_chars += processed_chars;
                    }
                    LayoutFit::OutOfBounds {
                        processed_chars, ..
                    } => {
                        total_processed_chars += processed_chars;

                        return LayoutFit::OutOfBounds {
                            processed_chars: total_processed_chars,
                            height: self.layout_height(init_cursor, *cursor),
                        };
                    }
                },
            }
        }

        LayoutFit::Fitting {
            processed_chars: total_processed_chars,
            height: self.layout_height(init_cursor, *cursor),
        }
    }

    pub fn layout_text(
        &self,
        text: &str,
        cursor: &mut Point,
        sink: &mut dyn LayoutSink,
    ) -> LayoutFit {
        let init_cursor = *cursor;
        let bottom = (self.bounds.y1 - self.padding_bottom).max(self.bounds.y0);
        let mut remaining_text = text;

        // Check if bounding box is high enough for at least one line.
        if cursor.y > bottom {
            sink.out_of_bounds();
            return LayoutFit::OutOfBounds {
                processed_chars: 0,
                height: 0,
            };
        }

        while !remaining_text.is_empty() {
            let span = Span::fit_horizontally(
                remaining_text,
                self.bounds.x1 - cursor.x,
                self.text_font,
                self.hyphen_font,
                self.line_breaking,
            );

            // Report the span at the cursor position.
            sink.text(*cursor, self, &remaining_text[..span.length]);

            // Continue with the rest of the remaining_text.
            remaining_text = &remaining_text[span.length + span.skip_next_chars..];

            // Advance the cursor horizontally.
            cursor.x += span.advance.x;

            if span.advance.y > 0 {
                // We're advancing to the next line.

                // Check if we should be appending a hyphen at this point.
                if span.insert_hyphen_before_line_break {
                    sink.hyphen(*cursor, self);
                }
                // Check the amount of vertical space we have left.
                if cursor.y + span.advance.y > bottom {
                    if !remaining_text.is_empty() {
                        // Append ellipsis to indicate more content is available, but only if we
                        // haven't already appended a hyphen.
                        let should_append_ellipsis =
                            matches!(self.page_breaking, PageBreaking::CutAndInsertEllipsis)
                                && !span.insert_hyphen_before_line_break;
                        if should_append_ellipsis {
                            sink.ellipsis(*cursor, self);
                        }
                        // TODO: This does not work in case we are the last
                        // fitting text token on the line, with more text tokens
                        // following and `text.is_empty() == true`.
                    }

                    // Report we are out of bounds and quit.
                    sink.out_of_bounds();

                    return LayoutFit::OutOfBounds {
                        processed_chars: text.len() - remaining_text.len(),
                        height: self.layout_height(init_cursor, *cursor),
                    };
                } else {
                    // Advance the cursor to the beginning of the next line.
                    cursor.x = self.bounds.x0;
                    cursor.y += span.advance.y;

                    // Report a line break. While rendering works using the cursor coordinates, we
                    // use explicit line-break reporting in the `Trace` impl.
                    sink.line_break(*cursor);
                }
            }
        }

        LayoutFit::Fitting {
            processed_chars: text.len(),
            height: self.layout_height(init_cursor, *cursor),
        }
    }

    fn layout_height(&self, init_cursor: Point, end_cursor: Point) -> i32 {
        self.padding_top
            + self.text_font.text_height()
            + (end_cursor.y - init_cursor.y)
            + self.padding_bottom
    }
}

pub enum LayoutFit {
    /// Entire content fits. Vertical size is returned in `height`.
    Fitting { processed_chars: usize, height: i32 },
    /// Content fits partially or not at all.
    OutOfBounds { processed_chars: usize, height: i32 },
}

impl LayoutFit {
    pub fn height(&self) -> i32 {
        match self {
            LayoutFit::Fitting { height, .. } => *height,
            LayoutFit::OutOfBounds { height, .. } => *height,
        }
    }
}

/// Visitor for text segment operations.
pub trait LayoutSink {
    fn text(&mut self, _cursor: Point, _layout: &TextLayout, _text: &str) {}
    fn hyphen(&mut self, _cursor: Point, _layout: &TextLayout) {}
    fn ellipsis(&mut self, _cursor: Point, _layout: &TextLayout) {}
    fn line_break(&mut self, _cursor: Point) {}
    fn out_of_bounds(&mut self) {}
}

pub struct TextNoOp;

impl LayoutSink for TextNoOp {}

pub struct TextRenderer;

impl LayoutSink for TextRenderer {
    fn text(&mut self, cursor: Point, layout: &TextLayout, text: &str) {
        display::text(
            cursor,
            text,
            layout.text_font,
            layout.text_color,
            layout.background_color,
        );
    }

    fn hyphen(&mut self, cursor: Point, layout: &TextLayout) {
        display::text(
            cursor,
            "-",
            layout.hyphen_font,
            layout.hyphen_color,
            layout.background_color,
        );
    }

    fn ellipsis(&mut self, cursor: Point, layout: &TextLayout) {
        display::text(
            cursor,
            "...",
            layout.ellipsis_font,
            layout.ellipsis_color,
            layout.background_color,
        );
    }
}

#[cfg(feature = "ui_debug")]
pub mod trace {
    use crate::ui::geometry::Point;

    use super::*;

    pub struct TraceSink<'a>(pub &'a mut dyn crate::trace::Tracer);

    impl<'a> LayoutSink for TraceSink<'a> {
        fn text(&mut self, _cursor: Point, _layout: &TextLayout, text: &str) {
            self.0.string(text);
        }

        fn hyphen(&mut self, _cursor: Point, _layout: &TextLayout) {
            self.0.string("-");
        }

        fn ellipsis(&mut self, _cursor: Point, _layout: &TextLayout) {
            self.0.string("...");
        }

        fn line_break(&mut self, _cursor: Point) {
            self.0.string("\n");
        }
    }
}

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum Op<'a> {
    /// Render text with current color and font.
    Text(&'a str),
    /// Set current text color.
    Color(Color),
    /// Set currently used font.
    Font(Font),
}

impl<'a> Op<'a> {
    pub fn skip_n_text_bytes(
        ops: impl Iterator<Item = Op<'a>>,
        skip_bytes: usize,
    ) -> impl Iterator<Item = Op<'a>> {
        let mut skipped = 0;

        ops.filter_map(move |op| match op {
            Op::Text(text) if skipped < skip_bytes => {
                skipped = skipped.saturating_add(text.len());
                if skipped > skip_bytes {
                    let leave_bytes = skipped - skip_bytes;
                    Some(Op::Text(&text[text.len() - leave_bytes..]))
                } else {
                    None
                }
            }
            op_to_pass_through => Some(op_to_pass_through),
        })
    }
}

#[derive(Debug, PartialEq, Eq)]
struct Span {
    /// How many characters from the input text this span is laying out.
    length: usize,
    /// How many chars from the input text should we skip before fitting the
    /// next span?
    skip_next_chars: usize,
    /// By how much to offset the cursor after this span. If the vertical offset
    /// is bigger than zero, it means we are breaking the line.
    advance: Offset,
    /// If we are breaking the line, should we insert a hyphen right after this
    /// span to indicate a word-break?
    insert_hyphen_before_line_break: bool,
}

impl Span {
    fn fit_horizontally(
        text: &str,
        max_width: i32,
        text_font: impl GlyphMetrics,
        hyphen_font: impl GlyphMetrics,
        breaking: LineBreaking,
    ) -> Self {
        const ASCII_LF: char = '\n';
        const ASCII_CR: char = '\r';
        const ASCII_SPACE: char = ' ';
        const ASCII_HYPHEN: char = '-';

        fn is_whitespace(ch: char) -> bool {
            ch == ASCII_SPACE || ch == ASCII_LF || ch == ASCII_CR
        }

        let hyphen_width = hyphen_font.char_width(ASCII_HYPHEN);

        // The span we return in case the line has to break. We mutate it in the
        // possible break points, and its initial value is returned in case no text
        // at all is fitting the constraints: zero length, zero width, full line
        // break.
        let mut line = Self {
            length: 0,
            advance: Offset::y(text_font.line_height()),
            insert_hyphen_before_line_break: false,
            skip_next_chars: 0,
        };

        let mut span_width = 0;
        let mut found_any_whitespace = false;

        let mut char_indices_iter = text.char_indices().peekable();
        // Iterating manually because we need a reference to the iterator inside the
        // loop.
        while let Some((i, ch)) = char_indices_iter.next() {
            let char_width = text_font.char_width(ch);

            // Consider if we could be breaking the line at this position.
            if is_whitespace(ch) {
                // Break before the whitespace, without hyphen.
                line.length = i;
                line.advance.x = span_width;
                line.insert_hyphen_before_line_break = false;
                line.skip_next_chars = 1;
                if ch == ASCII_CR {
                    // We'll be breaking the line, but advancing the cursor only by a half of the
                    // regular line height.
                    line.advance.y = text_font.line_height() / 2;
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
                let can_break_word = matches!(breaking, LineBreaking::BreakWordsAndInsertHyphen)
                    || !found_any_whitespace;
                if have_space_for_break && can_break_word {
                    // Break after this character, append hyphen.
                    line.length = match char_indices_iter.peek() {
                        Some((idx, _)) => *idx,
                        None => text.len(),
                    };
                    line.advance.x = span_width + char_width;
                    line.insert_hyphen_before_line_break = true;
                    line.skip_next_chars = 0;
                }
            }

            span_width += char_width;
        }

        // The whole text is fitting.
        Self {
            length: text.len(),
            advance: Offset::x(span_width),
            insert_hyphen_before_line_break: false,
            skip_next_chars: 0,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    pub struct Fixed {
        pub width: i32,
        pub height: i32,
    }

    impl GlyphMetrics for Fixed {
        fn char_width(&self, _ch: char) -> i32 {
            self.width
        }

        fn line_height(&self) -> i32 {
            self.height
        }
    }

    const FIXED_FONT: Fixed = Fixed {
        width: 1,
        height: 1,
    };

    #[test]
    fn test_span() {
        assert_eq!(spans_from("hello", 5), vec![("hello", false)]);
        assert_eq!(spans_from("", 5), vec![("", false)]);
        assert_eq!(
            spans_from("hello world", 5),
            vec![("hello", false), ("world", false)]
        );
        assert_eq!(
            spans_from("hello\nworld", 5),
            vec![("hello", false), ("world", false)]
        );
    }

    #[test]
    #[ignore]
    fn test_leading_trailing() {
        assert_eq!(
            spans_from("\nhello\nworld\n", 5),
            vec![("", false), ("hello", false), ("world", false), ("", false)]
        );
    }

    #[test]
    fn test_long_word() {
        assert_eq!(
            spans_from("Down with the establishment!", 5),
            vec![
                ("Down", false),
                ("with", false),
                ("the", false),
                ("esta", true),
                ("blis", true),
                ("hmen", true),
                ("t!", false),
            ]
        );
    }

    #[test]
    fn test_char_boundary() {
        assert_eq!(
            spans_from("+ěščřžýáíé", 5),
            vec![("+ěšč", true), ("řžýá", true), ("íé", false)]
        );
    }

    fn spans_from(text: &str, max_width: i32) -> Vec<(&str, bool)> {
        let mut spans = vec![];
        let mut remaining_text = text;
        loop {
            let span = Span::fit_horizontally(
                remaining_text,
                max_width,
                FIXED_FONT,
                FIXED_FONT,
                LineBreaking::BreakAtWhitespace,
            );
            spans.push((
                &remaining_text[..span.length],
                span.insert_hyphen_before_line_break,
            ));
            remaining_text = &remaining_text[span.length + span.skip_next_chars..];
            if remaining_text.is_empty() {
                break;
            }
        }
        spans
    }
}

use core::{
    iter::{Enumerate, Peekable},
    slice,
};

use heapless::LinearMap;

use crate::ui::{
    component::{Component, Event, EventCtx, Never},
    display,
    display::{Color, Font},
    geometry::{Offset, Point, Rect},
};

use super::model::theme;

pub const MAX_ARGUMENTS: usize = 6;

pub struct Text<F, T> {
    layout: TextLayout,
    format: F,
    args: LinearMap<&'static [u8], T, MAX_ARGUMENTS>,
}

impl<F, T> Text<F, T> {
    pub fn new(area: Rect, format: F) -> Self {
        Self {
            layout: TextLayout::new(area),
            format,
            args: LinearMap::new(),
        }
    }

    pub fn format(mut self, format: F) -> Self {
        self.format = format;
        self
    }

    pub fn with(mut self, key: &'static [u8], value: T) -> Self {
        if self.args.insert(key, value).is_err() {
            // Map is full, ignore.
            #[cfg(feature = "ui_debug")]
            panic!("Text args map is full");
        }
        self
    }

    pub fn with_text_font(mut self, text_font: Font) -> Self {
        self.layout.text_font = text_font;
        self
    }

    pub fn with_text_color(mut self, text_color: Color) -> Self {
        self.layout.text_color = text_color;
        self
    }

    pub fn with_line_breaking(mut self, line_breaking: LineBreaking) -> Self {
        self.layout.line_breaking = line_breaking;
        self
    }

    pub fn with_page_breaking(mut self, page_breaking: PageBreaking) -> Self {
        self.layout.page_breaking = page_breaking;
        self
    }

    pub fn layout_mut(&mut self) -> &mut TextLayout {
        &mut self.layout
    }
}

impl<F, T> Text<F, T>
where
    F: AsRef<[u8]>,
    T: AsRef<[u8]>,
{
    fn layout_content(&self, sink: &mut dyn LayoutSink) {
        self.layout.layout_formatted(
            self.format.as_ref(),
            |arg| match arg {
                Token::Literal(literal) => Some(Op::Text(literal)),
                Token::Argument(b"mono") => Some(Op::Font(theme::FONT_MONO)),
                Token::Argument(b"bold") => Some(Op::Font(theme::FONT_BOLD)),
                Token::Argument(b"normal") => Some(Op::Font(theme::FONT_NORMAL)),
                Token::Argument(argument) => self
                    .args
                    .get(argument)
                    .map(|value| Op::Text(value.as_ref())),
            },
            sink,
        );
    }
}

impl<F, T> Component for Text<F, T>
where
    F: AsRef<[u8]>,
    T: AsRef<[u8]>,
{
    type Msg = Never;

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    fn paint(&mut self) {
        self.layout_content(&mut TextRenderer);
    }
}

#[cfg(feature = "ui_debug")]
mod trace {
    use super::*;

    pub struct TraceSink<'a>(pub &'a mut dyn crate::trace::Tracer);

    impl<'a> LayoutSink for TraceSink<'a> {
        fn text(&mut self, _cursor: Point, _layout: &TextLayout, text: &[u8]) {
            self.0.bytes(text);
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

    pub struct TraceText<'a, F, T>(pub &'a Text<F, T>);

    impl<'a, F, T> crate::trace::Trace for TraceText<'a, F, T>
    where
        F: AsRef<[u8]>,
        T: AsRef<[u8]>,
    {
        fn trace(&self, d: &mut dyn crate::trace::Tracer) {
            self.0.layout_content(&mut TraceSink(d));
        }
    }
}

#[cfg(feature = "ui_debug")]
impl<F, T> crate::trace::Trace for Text<F, T>
where
    F: AsRef<[u8]>,
    T: AsRef<[u8]>,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.open("Text");
        t.field("content", &trace::TraceText(self));
        t.close();
    }
}

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
}

impl TextLayout {
    pub fn new(bounds: Rect) -> Self {
        Self {
            bounds,
            background_color: theme::BG,
            text_color: theme::FG,
            text_font: theme::FONT_NORMAL,
            line_breaking: LineBreaking::BreakAtWhitespace,
            hyphen_font: theme::FONT_BOLD,
            hyphen_color: theme::GREY_LIGHT,
            page_breaking: PageBreaking::CutAndInsertEllipsis,
            ellipsis_font: theme::FONT_BOLD,
            ellipsis_color: theme::GREY_LIGHT,
        }
    }

    pub fn initial_cursor(&self) -> Point {
        Point::new(
            self.bounds.top_left().x,
            self.bounds.top_left().y + self.text_font.line_height(),
        )
    }

    pub fn layout_formatted<'f, 'o, F, I>(
        self,
        format: &'f [u8],
        resolve: F,
        sink: &mut dyn LayoutSink,
    ) -> LayoutFit
    where
        F: Fn(Token<'f>) -> I,
        I: IntoIterator<Item = Op<'o>>,
    {
        let mut cursor = self.initial_cursor();

        self.layout_op_stream(
            &mut Tokenizer::new(format).flat_map(resolve),
            &mut cursor,
            sink,
        )
    }

    pub fn layout_op_stream<'o>(
        mut self,
        ops: &mut dyn Iterator<Item = Op<'o>>,
        cursor: &mut Point,
        sink: &mut dyn LayoutSink,
    ) -> LayoutFit {
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
                    LayoutFit::Fitting { processed_chars } => {
                        total_processed_chars += processed_chars;
                    }
                    LayoutFit::OutOfBounds { processed_chars } => {
                        total_processed_chars += processed_chars;

                        return LayoutFit::OutOfBounds {
                            processed_chars: total_processed_chars,
                        };
                    }
                },
            }
        }

        LayoutFit::Fitting {
            processed_chars: total_processed_chars,
        }
    }

    pub fn layout_text(
        &self,
        text: &[u8],
        cursor: &mut Point,
        sink: &mut dyn LayoutSink,
    ) -> LayoutFit {
        let mut remaining_text = text;

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
                if cursor.y + span.advance.y > self.bounds.y1 {
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
        }
    }
}

pub enum LayoutFit {
    Fitting { processed_chars: usize },
    OutOfBounds { processed_chars: usize },
}

/// Visitor for text segment operations.
pub trait LayoutSink {
    fn text(&mut self, _cursor: Point, _layout: &TextLayout, _text: &[u8]) {}
    fn hyphen(&mut self, _cursor: Point, _layout: &TextLayout) {}
    fn ellipsis(&mut self, _cursor: Point, _layout: &TextLayout) {}
    fn line_break(&mut self, _cursor: Point) {}
    fn out_of_bounds(&mut self) {}
}

pub struct TextNoop;

impl LayoutSink for TextNoop {}

pub struct TextRenderer;

impl LayoutSink for TextRenderer {
    fn text(&mut self, cursor: Point, layout: &TextLayout, text: &[u8]) {
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
            b"-",
            layout.hyphen_font,
            layout.hyphen_color,
            layout.background_color,
        );
    }

    fn ellipsis(&mut self, cursor: Point, layout: &TextLayout) {
        display::text(
            cursor,
            b"...",
            layout.ellipsis_font,
            layout.ellipsis_color,
            layout.background_color,
        );
    }
}

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum Token<'a> {
    /// Process literal text content.
    Literal(&'a [u8]),
    /// Process argument with specified descriptor.
    Argument(&'a [u8]),
}

/// Processes a format string into an iterator of `Token`s.
///
/// # Example
///
/// ```
/// let parser = Tokenizer::new("Nice to meet {you}, where you been?");
/// assert!(matches!(parser.next(), Some(Token::Literal("Nice to meet "))));
/// assert!(matches!(parser.next(), Some(Token::Argument("you"))));
/// assert!(matches!(parser.next(), Some(Token::Literal(", where you been?"))));
/// ```
pub struct Tokenizer<'a> {
    input: &'a [u8],
    inner: Peekable<Enumerate<slice::Iter<'a, u8>>>,
}

impl<'a> Tokenizer<'a> {
    /// Create a new tokenizer for bytes of a formatting string `input`,
    /// returning an iterator.
    pub fn new(input: &'a [u8]) -> Self {
        Self {
            input,
            inner: input.iter().enumerate().peekable(),
        }
    }
}

impl<'a> Iterator for Tokenizer<'a> {
    type Item = Token<'a>;

    fn next(&mut self) -> Option<Self::Item> {
        const ASCII_OPEN_BRACE: u8 = b'{';
        const ASCII_CLOSED_BRACE: u8 = b'}';

        match self.inner.next() {
            // Argument token is starting. Read until we find '}', then parse the content between
            // the braces and return the token. If we encounter the end of string before the closing
            // brace, quit.
            Some((open, &ASCII_OPEN_BRACE)) => loop {
                match self.inner.next() {
                    Some((close, &ASCII_CLOSED_BRACE)) => {
                        break Some(Token::Argument(&self.input[open + 1..close]));
                    }
                    None => {
                        break None;
                    }
                    _ => {}
                }
            },
            // Literal token is starting. Read until we find '{' or the end of string, and return
            // the token. Use `peek()` for matching the opening brace, se we can keep it
            // in the iterator for the above code.
            Some((start, _)) => loop {
                match self.inner.peek() {
                    Some(&(open, &ASCII_OPEN_BRACE)) => {
                        break Some(Token::Literal(&self.input[start..open]));
                    }
                    None => {
                        break Some(Token::Literal(&self.input[start..]));
                    }
                    _ => {
                        self.inner.next();
                    }
                }
            },
            None => None,
        }
    }
}

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum Op<'a> {
    /// Render text with current color and font.
    Text(&'a [u8]),
    /// Set current text color.
    Color(Color),
    /// Set currently used font.
    Font(Font),
}

impl<'a> Op<'a> {
    fn skip_n_text_bytes(
        ops: impl Iterator<Item = Op<'a>>,
        skip_bytes: usize,
    ) -> impl Iterator<Item = Op<'a>> {
        let mut skipped = 0;

        ops.filter_map(move |op| match op {
            Op::Text(text) if skipped < skip_bytes => {
                skipped = skipped.saturating_add(text.len());
                if skipped > skip_bytes {
                    let leave_bytes = skipped - skip_bytes;
                    Some(Op::Text(&text[..text.len() - leave_bytes]))
                } else {
                    None
                }
            }
            op_to_pass_through => Some(op_to_pass_through),
        })
    }
}

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
        text: &[u8],
        max_width: i32,
        text_font: Font,
        hyphen_font: Font,
        breaking: LineBreaking,
    ) -> Self {
        const ASCII_LF: u8 = b'\n';
        const ASCII_CR: u8 = b'\r';
        const ASCII_SPACE: u8 = b' ';
        const ASCII_HYPHEN: u8 = b'-';

        fn is_whitespace(ch: u8) -> bool {
            ch == ASCII_SPACE || ch == ASCII_LF || ch == ASCII_CR
        }

        let hyphen_width = hyphen_font.text_width(&[ASCII_HYPHEN]);

        // The span we return in case the line has to break. We mutate it in the
        // possible break points, and its initial value is returned in case no text
        // at all is fitting the constraints: zero length, zero width, full line
        // break.
        let mut line = Self {
            length: 0,
            advance: Offset::new(0, text_font.line_height()),
            insert_hyphen_before_line_break: false,
            skip_next_chars: 0,
        };

        let mut span_width = 0;
        let mut found_any_whitespace = false;

        for (i, &ch) in text.iter().enumerate() {
            let char_width = text_font.text_width(&[ch]);

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
                    line.length = i + 1;
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
            advance: Offset::new(span_width, 0),
            insert_hyphen_before_line_break: false,
            skip_next_chars: 0,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn tokenizer_yields_expected_tokens() {
        use std::array::IntoIter;

        assert!(Tokenizer::new(b"").eq(IntoIter::new([])));
        assert!(Tokenizer::new(b"x").eq(IntoIter::new([Token::Literal(b"x")])));
        assert!(Tokenizer::new(b"x\0y").eq(IntoIter::new([Token::Literal("x\0y".as_bytes())])));
        assert!(Tokenizer::new(b"{").eq(IntoIter::new([])));
        assert!(Tokenizer::new(b"x{").eq(IntoIter::new([Token::Literal(b"x")])));
        assert!(Tokenizer::new(b"x{y").eq(IntoIter::new([Token::Literal(b"x")])));
        assert!(Tokenizer::new(b"{}").eq(IntoIter::new([Token::Argument(b"")])));
        assert!(Tokenizer::new(b"x{}y{").eq(IntoIter::new([
            Token::Literal(b"x"),
            Token::Argument(b""),
            Token::Literal(b"y"),
        ])));
        assert!(Tokenizer::new(b"{\0}").eq(IntoIter::new([Token::Argument("\0".as_bytes()),])));
        assert!(Tokenizer::new(b"{{y}").eq(IntoIter::new([Token::Argument(b"{y"),])));
        assert!(Tokenizer::new(b"{{{{xyz").eq(IntoIter::new([])));
        assert!(Tokenizer::new(b"x{}{{}}}}").eq(IntoIter::new([
            Token::Literal(b"x"),
            Token::Argument(b""),
            Token::Argument(b"{"),
            Token::Literal(b"}}}"),
        ])));
    }
}

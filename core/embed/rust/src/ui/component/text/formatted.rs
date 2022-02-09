use core::{
    iter::{Enumerate, Peekable},
    slice,
};

use heapless::LinearMap;

use crate::ui::{
    component::{Component, Event, EventCtx, Never},
    display::{Color, Font},
    geometry::Rect,
};

use super::layout::{
    DefaultTextTheme, LayoutFit, LayoutSink, LineBreaking, Op, PageBreaking, TextLayout,
    TextRenderer,
};

pub const MAX_ARGUMENTS: usize = 6;

pub struct FormattedText<F, T> {
    layout: TextLayout,
    format: F,
    args: LinearMap<&'static str, T, MAX_ARGUMENTS>,
    char_offset: usize,
}

impl<F, T> FormattedText<F, T> {
    pub fn new<D: DefaultTextTheme>(format: F) -> Self {
        Self {
            format,
            layout: TextLayout::new::<D>(),
            args: LinearMap::new(),
            char_offset: 0,
        }
    }

    pub fn with(mut self, key: &'static str, value: T) -> Self {
        if self.args.insert(key, value).is_err() {
            #[cfg(feature = "ui_debug")]
            panic!("text args map is full");
        }
        self
    }

    pub fn with_format(mut self, format: F) -> Self {
        self.format = format;
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

    pub fn set_char_offset(&mut self, char_offset: usize) {
        self.char_offset = char_offset;
    }

    pub fn char_offset(&mut self) -> usize {
        self.char_offset
    }

    pub fn layout_mut(&mut self) -> &mut TextLayout {
        &mut self.layout
    }
}

impl<F, T> FormattedText<F, T>
where
    F: AsRef<str>,
    T: AsRef<str>,
{
    pub fn layout_content(&self, sink: &mut dyn LayoutSink) -> LayoutFit {
        let mut cursor = self.layout.initial_cursor();
        let mut ops = Op::skip_n_text_bytes(
            Tokenizer::new(self.format.as_ref()).flat_map(|arg| match arg {
                Token::Literal(literal) => Some(Op::Text(literal)),
                Token::Argument("mono") => Some(Op::Font(self.layout.mono_font)),
                Token::Argument("bold") => Some(Op::Font(self.layout.bold_font)),
                Token::Argument("normal") => Some(Op::Font(self.layout.normal_font)),
                Token::Argument("medium") => Some(Op::Font(self.layout.medium_font)),
                Token::Argument(argument) => self
                    .args
                    .get(argument)
                    .map(|value| Op::Text(value.as_ref())),
            }),
            self.char_offset,
        );
        self.layout.layout_ops(&mut ops, &mut cursor, sink)
    }
}

impl<F, T> Component for FormattedText<F, T>
where
    F: AsRef<str>,
    T: AsRef<str>,
{
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.layout.bounds = bounds;
        self.layout.bounds
    }

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    fn paint(&mut self) {
        self.layout_content(&mut TextRenderer);
    }

    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        sink(self.layout.bounds)
    }
}

#[cfg(feature = "ui_debug")]
pub mod trace {
    use crate::ui::component::text::layout::trace::TraceSink;

    use super::*;

    pub struct TraceText<'a, F, T>(pub &'a FormattedText<F, T>);

    impl<'a, F, T> crate::trace::Trace for TraceText<'a, F, T>
    where
        F: AsRef<str>,
        T: AsRef<str>,
    {
        fn trace(&self, d: &mut dyn crate::trace::Tracer) {
            self.0.layout_content(&mut TraceSink(d));
        }
    }
}

#[cfg(feature = "ui_debug")]
impl<F, T> crate::trace::Trace for FormattedText<F, T>
where
    F: AsRef<str>,
    T: AsRef<str>,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.open("Text");
        t.field("content", &trace::TraceText(self));
        t.close();
    }
}

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum Token<'a> {
    /// Process literal text content.
    Literal(&'a str),
    /// Process argument with specified descriptor.
    Argument(&'a str),
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
    input: &'a str,
    inner: Peekable<Enumerate<slice::Iter<'a, u8>>>,
}

impl<'a> Tokenizer<'a> {
    /// Create a new tokenizer for bytes of a formatting string `input`,
    /// returning an iterator.
    pub fn new(input: &'a str) -> Self {
        assert!(input.is_ascii());
        Self {
            input,
            inner: input.as_bytes().iter().enumerate().peekable(),
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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn tokenizer_yields_expected_tokens() {
        assert!(Tokenizer::new("").eq([]));
        assert!(Tokenizer::new("x").eq([Token::Literal("x")]));
        assert!(Tokenizer::new("x\0y").eq([Token::Literal("x\0y")]));
        assert!(Tokenizer::new("{").eq([]));
        assert!(Tokenizer::new("x{").eq([Token::Literal("x")]));
        assert!(Tokenizer::new("x{y").eq([Token::Literal("x")]));
        assert!(Tokenizer::new("{}").eq([Token::Argument("")]));
        assert!(Tokenizer::new("x{}y{").eq([
            Token::Literal("x"),
            Token::Argument(""),
            Token::Literal("y"),
        ]));
        assert!(Tokenizer::new("{\0}").eq([Token::Argument("\0"),]));
        assert!(Tokenizer::new("{{y}").eq([Token::Argument("{y"),]));
        assert!(Tokenizer::new("{{{{xyz").eq([]));
        assert!(Tokenizer::new("x{}{{}}}}").eq([
            Token::Literal("x"),
            Token::Argument(""),
            Token::Argument("{"),
            Token::Literal("}}}"),
        ]));
    }
}

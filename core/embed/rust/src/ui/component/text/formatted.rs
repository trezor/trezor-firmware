use core::{
    iter::{Enumerate, Peekable, self},
    slice,
};

use heapless::LinearMap;

use crate::ui::{
    component::{Component, Event, EventCtx, Never},
    geometry::Rect, display::{Font, Color},
};

use super::{layout::{Op, TextStyle}, iter::{LayoutFit, Span, break_text_to_spans}};

pub const MAX_ARGUMENTS: usize = 6;

pub struct FormattedText<F, T> {
    style: TextStyle,
    param_style: TextStyle,
    format: F,
    args: LinearMap<&'static str, T, MAX_ARGUMENTS>,
    char_offset: usize,
    bounds: Rect,
}

impl<F, T> FormattedText<F, T> {
    pub const fn new(style: TextStyle, format: F) -> Self {
        Self {
            format,
            style,
            param_style: style,
            args: LinearMap::new(),
            char_offset: 0,
            bounds: Rect::zero(),
        }
    }

    pub fn with_param_style(self, style: TextStyle) -> Self {
        Self {
            param_style: style,
            ..self
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

    pub fn set_char_offset(&mut self, char_offset: usize) {
        self.char_offset = char_offset;
    }

    pub fn char_offset(&mut self) -> usize {
        self.char_offset
    }
}

impl<F, T> FormattedText<F, T>
where
    F: AsRef<str>,
    T: AsRef<str>,
{
    pub fn ops(&self) -> impl Iterator<Item = Op> + '_ {
        Op::skip_n_text_bytes(
            Tokenizer::new(self.format.as_ref()).flat_map(|arg| match arg {
                Token::Literal(literal) => Some((self.style.text_font, literal)),
                Token::Argument(argument) => self
                    .args
                    .get(argument)
                    .map(|value| (self.param_style.text_font, value.as_ref())),
            }).flat_map(|(font, text)| [Op::Font(font), Op::Text(text)]),
            self.char_offset,
        )
    }

    pub fn spans(&self) -> impl Iterator<Item = (Font, Color, Span)>
    {
        let mut font = self.style.text_font;
        let mut color = self.style.text_color;
        let mut offset = 0;

        self.ops().filter_map(move |op| {
            match op {
                Op::Color(c) => {
                    color = c;
                    None
                }
                Op::Font(f) => {
                    font = f;
                    None
                }
                Op::Text(text) => {
                    let spans = break_text_to_spans(text, font, self.style.line_breaking, self.bounds.width(), offset);
                    Some(spans.map(move |s| {
                        (font, color, s)
                    }))
                }
            }
        }).flatten()
    }

    pub fn fit(&mut self) -> LayoutFit {
        let mut ops = self.ops();
        //self.style.fit_ops(&mut ops, self.bounds.size())
        //TODO
        LayoutFit::empty()
    }
}

impl<F, T> Component for FormattedText<F, T>
where
    F: AsRef<str>,
    T: AsRef<str>,
{
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.bounds = bounds;
        self.bounds
    }

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    fn paint(&mut self) {
        let mut ops = self.ops();
        //TODOself.style.render_ops(&mut ops, self.bounds);
    }

    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        sink(self.bounds)
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
        for op in self.ops() {
            if let Op::Text(text) = op {
                t.string(text);
            }
        }
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

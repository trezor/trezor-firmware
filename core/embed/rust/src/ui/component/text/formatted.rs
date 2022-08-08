use core::{
    iter::{Enumerate, Peekable},
    slice,
};

use heapless::LinearMap;

use crate::ui::{
    component::{Component, Event, EventCtx, Never},
    display::{Color, Font},
    geometry::{Offset, Rect},
};

use super::layout::{
    LayoutFit, LayoutSink, LineBreaking, Op, PageBreaking, TextLayout, TextRenderer, TextStyle,
};

pub const MAX_ARGUMENTS: usize = 6;

#[derive(Clone)]
pub struct FormattedText<F, T> {
    layout: TextLayout,
    fonts: FormattedFonts,
    format: F,
    args: LinearMap<&'static str, T, MAX_ARGUMENTS>,
    icon_args: LinearMap<&'static str, &'static [u8], MAX_ARGUMENTS>,
    /// Keeps track of "cursor" position, so that we can paginate
    /// by skipping this amount of characters from the beginning.
    char_offset: usize,
}

#[derive(Clone)]
pub struct FormattedFonts {
    /// Font used to format `{normal}`.
    pub normal: Font,
    /// Font used to format `{medium}`.
    pub medium: Font,
    /// Font used to format `{bold}`.
    pub bold: Font,
    /// Font used to format `{mono}`.
    pub mono: Font,
}

impl<F, T> FormattedText<F, T> {
    pub fn new(style: TextStyle, fonts: FormattedFonts, format: F) -> Self {
        Self {
            format,
            fonts,
            layout: TextLayout::new(style),
            args: LinearMap::new(),
            icon_args: LinearMap::new(),
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

    pub fn with_icon(mut self, key: &'static str, value: &'static [u8]) -> Self {
        if self.icon_args.insert(key, value).is_err() {
            #[cfg(feature = "ui_debug")]
            panic!("icon args map is full");
        }
        self
    }

    pub fn with_format(mut self, format: F) -> Self {
        self.format = format;
        self
    }

    pub fn with_text_font(mut self, text_font: Font) -> Self {
        self.layout.style.text_font = text_font;
        self
    }

    pub fn with_text_color(mut self, text_color: Color) -> Self {
        self.layout.style.text_color = text_color;
        self
    }

    pub fn with_line_breaking(mut self, line_breaking: LineBreaking) -> Self {
        self.layout.style.line_breaking = line_breaking;
        self
    }

    /// Whether text will have ellipsis at the end of each the page.
    /// Currently it will have it by default.
    pub fn with_ellipsis(mut self, have_it: bool) -> Self {
        self.layout.style.page_breaking = if have_it {
            PageBreaking::CutAndInsertEllipsis
        } else {
            PageBreaking::Cut
        };
        self
    }

    /// Equals to changing the page so that we know what
    /// content to render next.
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
    /// Tokenizing `self.format` and turning it into the list of `Op`s
    /// which will be sent to `LayoutSink`.
    /// It equals to painting the content when `sink` is `TextRenderer`.
    pub fn layout_content(&self, sink: &mut dyn LayoutSink) -> LayoutFit {
        // let all_ops = Tokenizer::new(self.format.as_ref()).flat_map(|arg|
        // self.token_to_op(&arg)); TODO: It would be very nice to move all the
        // logic to `fn token_to_op(&self, token: &Token) -> Option<Op>`, but it
        // had some issues with lifetimes I could not solve
        let all_ops = Tokenizer::new(self.format.as_ref()).flat_map(|arg| match arg {
            // TODO: could add ways to:
            // - underscore the text {Text::underscore}
            // - strikethrough the text {Text::strikethrough}
            // - bullet-point on the line {bullet_point}
            // - draw horizontal line {horizontal_line}
            // - change line-spacing {Line-spacing::10px}
            // - add default line offset {Line-offset::3px}

            // NOTE / TODO: we agreed not to do these things here in production,
            // but the ideas here apply for the common things that we might
            // want to support "somewhere" and "somehow" - like the ability to
            // change font, add icon etc.

            // Normal text encountered
            Token::Literal(literal) => Some(Op::Text(literal)),
            // Force going to the next page
            // `{next_page}`
            Token::Argument(next_page) if next_page == "next_page" => Some(Op::NextPage),
            // Changing currently used font
            // e.g. `{Font::bold}`
            Token::Argument(font) if font.starts_with("Font::") => {
                let font_name = &font["Font::".len()..];
                match font_name {
                    "mono" => Some(Op::Font(self.fonts.mono)),
                    "bold" => Some(Op::Font(self.fonts.bold)),
                    "normal" => Some(Op::Font(self.fonts.normal)),
                    "medium" => Some(Op::Font(self.fonts.medium)),
                    _ => {
                        #[cfg(feature = "ui_debug")]
                        panic!("Unsupported font name");
                    }
                }
            }
            // Offsetting cursor position
            // e.g. `{Offset::x::3}`
            Token::Argument(offset) if offset.starts_with("Offset::") => {
                let offset_args = &offset["Offset::".len()..];
                let axis = &offset_args[..1];
                // TODO: some error handling here?
                let value = offset_args[3..].parse::<i32>().unwrap();
                match axis {
                    "x" => Some(Op::CursorOffset(Offset::x(value))),
                    "y" => Some(Op::CursorOffset(Offset::y(value))),
                    _ => {
                        #[cfg(feature = "ui_debug")]
                        panic!("Unsupported offset axis");
                    }
                }
            }
            // Drawing icon
            // e.g. `{Icon::user}`, .with_icon("user", theme::ICON_USER)
            // TODO: currently we always draw it with left-bottom corner on the cursor,
            // we might support drawing it with other corners
            // (however, one might hack around something like this by using `Offset::x`
            // and `Offset::y` before and after drawing the icon)
            // TODO: we could centralize all the icons here and connect them
            // just with strings, so that users do not need to supply the &[u8] icon data
            Token::Argument(icon) if icon.starts_with("Icon::") => {
                let icon_name = &icon["Icon::".len()..];
                self.icon_args.get(icon_name).map(|value| Op::Icon(value))
            }
            // Text with argument
            // e.g. `{address}`, .with("address", "abcd...")
            // TODO: when arg is not found, we just do not display it,
            // shouldn't we trigger some exception?
            // This branch is also triggered when users input some unsupported
            // operation like {Unsupported::black}
            Token::Argument(argument) => self
                .args
                .get(argument)
                .map(|value| Op::Text(value.as_ref())),
        });
        // Accounting for pagination by skipping the `char_offset` characters from the
        // beginning.
        let mut ops = Op::skip_n_content_bytes(all_ops, self.char_offset);
        let mut cursor = self.layout.initial_cursor();
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

use super::iter::{break_text_to_spans, fit_text, Appendix, GlyphMetrics, LayoutFit};
use crate::ui::{
    display,
    display::{Color, Font},
    geometry::{Offset, Point, Rect, Insets},
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

#[derive(Copy, Clone)]
pub struct TextStyle {
    /// Text font ID. Can be overridden by `Op::Font`.
    pub text_font: Font,
    /// Text color. Can be overridden by `Op::Color`.
    pub text_color: Color,
    /// Background color.
    pub background_color: Color,

    /// Foreground color used for drawing the hyphen.
    pub hyphen_color: Color,
    /// Foreground color used for drawing the ellipsis.
    pub ellipsis_color: Color,

    /// Specifies which line-breaking strategy to use.
    pub line_breaking: LineBreaking,
    /// Specifies what to do at the end of the page.
    pub page_breaking: PageBreaking,
}

impl TextStyle {
    pub const fn new(
        text_font: Font,
        text_color: Color,
        background_color: Color,
        hyphen_color: Color,
        ellipsis_color: Color,
    ) -> Self {
        TextStyle {
            text_font,
            text_color,
            background_color,
            hyphen_color,
            ellipsis_color,
            line_breaking: LineBreaking::BreakAtWhitespace,
            page_breaking: PageBreaking::CutAndInsertEllipsis,
        }
    }

    fn initial_cursor(&self, area: Rect, initial_offset: i32) -> Point {
        area.top_left() + Offset::new(initial_offset, self.text_font.text_height())
    }

    pub fn fit_text(&self, text: &str, bounds: Offset, initial_offset: i32) -> LayoutFit {
        fit_text(
            text,
            self.text_font,
            self.line_breaking,
            bounds,
            initial_offset,
        )
    }

    pub fn render_text(&self, text: &str, area: Rect, initial_offset: i32) -> LayoutFit {
        let mut cursor = self.initial_cursor(area, initial_offset);
        let line_height = self.text_font.line_height();
        let mut height = 0;
        let mut chars = 0;
        let mut final_offset = initial_offset;
        for span in break_text_to_spans(
            text,
            self.text_font,
            self.line_breaking,
            area.width(),
            initial_offset,
        ) {
            display::text(
                cursor,
                span.text,
                self.text_font,
                self.text_color,
                self.background_color,
            );
            height += line_height;
            chars += span.text.len();
            final_offset = span.width;
            if matches!(span.append, Appendix::Hyphen) {
                display::text(
                    cursor + Offset::x(span.width),
                    "-",
                    self.text_font,
                    self.hyphen_color,
                    self.background_color,
                );
            }
            cursor = Point::new(0, cursor.y + line_height);
            if !area.contains(cursor) {
                break;
            }
        }
        LayoutFit {
            height,
            chars,
            final_offset,
        }
    }

    pub fn fit_ops<'o>(&self, ops: &mut dyn Iterator<Item = Op<'o>>, bounds: Offset) -> LayoutFit {
        let mut height = 0;
        let mut chars = 0;
        let mut offset = 0;
        let mut font = self.text_font;
        for op in ops {
            match op {
                Op::Text(text) => {
                    let fit = fit_text(text, font, self.line_breaking, bounds, offset);
                    if fit.chars == 0 {
                        break;
                    }
                    chars += fit.chars;
                    height += fit.height;
                    offset = fit.final_offset;
                    bounds = bounds - Offset::y(fit.height);
                }
                Op::Font(f) => {
                    font = f;
                }
                _ => {}
            }
        }
        LayoutFit {
            height,
            chars,
            final_offset: offset,
        }
    }

    pub fn render_ops<'o>(&self, ops: &mut dyn Iterator<Item = Op<'o>>, area: Rect) -> LayoutFit {
        let mut remaining = area;
        let mut text_style = self.clone();
        let mut offset = 0;
        let mut total_processed_chars = 0;

        for op in ops {
            match op {
                Op::Color(color) => {
                    text_style.text_color = color;
                }
                Op::Font(font) => {
                    text_style.text_font = font;
                }
                Op::Text(text) => {
                    let fit = text_style.render_text(text, remaining, offset);
                    if fit.chars == 0 {
                        break;
                    }
                    remaining = remaining.inset(Insets::top(fit.height));
                    total_processed_chars += fit.chars;
                    offset = fit.final_offset;
                }
            }
        }
        LayoutFit {
            height: area.height() - remaining.height(),
            chars: total_processed_chars,
            final_offset: offset,
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

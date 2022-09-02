use super::iter::{break_text_to_spans, LayoutFit, Span, SpanEnd};
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
        Self {
            text_font,
            text_color,
            background_color,
            hyphen_color,
            ellipsis_color,
            line_breaking: LineBreaking::BreakAtWhitespace,
            page_breaking: PageBreaking::CutAndInsertEllipsis,
        }
    }

    pub fn initial_cursor(&self, area: Rect) -> Point {
        area.top_left() + Offset::new(0, self.text_font.text_height())
    }

    pub fn spans<'a>(
        &self,
        text: &'a str,
        available_width: i32,
        initial_offset: i32,
    ) -> impl Iterator<Item = Span<'a>> {
        break_text_to_spans(
            text,
            self.text_font,
            self.line_breaking,
            available_width,
            initial_offset,
        )
    }

    pub fn fit_text(&self, text: &str, bounds: Offset, initial_offset: i32) -> LayoutFit {
        LayoutFit::of(
            self.spans(text, bounds.x, initial_offset)
                .take(self.text_font.max_lines(bounds.y)),
        )
    }

    pub fn render_text(&self, text: &str, area: Rect) -> Point {
        let cursor = self.initial_cursor(area);
        self.render_text_at(text, area, cursor)
    }

    pub fn render_text_at(&self, text: &str, area: Rect, mut cursor: Point) -> Point {
        let initial_offset = cursor.x - area.x0;
        let line_height = self.text_font.line_height();
        for span in self.spans(text, area.width(), initial_offset) {
            display::text(
                cursor,
                span.text,
                self.text_font,
                self.text_color,
                self.background_color,
            );
            match span.end {
                SpanEnd::HyphenAndBreak => {
                    display::text(
                        cursor + Offset::x(span.width),
                        "-",
                        self.text_font,
                        self.hyphen_color,
                        self.background_color,
                    );
                    cursor = Point::new(area.x0, cursor.y + line_height);
                }
                SpanEnd::LineBreak => {
                    cursor = Point::new(area.x0, cursor.y + line_height);
                }
                SpanEnd::Continue => {
                    cursor.x += span.width;
                }
            }
            // If the cursor goes _below_ the area, we stop rendering.
            // We do not care about cursor moving right of area, because our spans are
            // guaranteed not to render anything there.
            if cursor.y > area.y1 {
                break;
            }
        }
        cursor
    }
}

use crate::ui::{
    display::{toif::Icon, Color, Font, GlyphMetrics},
    geometry::{Alignment, Alignment2D, Dimensions, Offset, Point, Rect},
    shape,
    shape::Renderer,
};

const ELLIPSIS: &str = "...";

#[derive(Copy, Clone)]
pub enum LineBreaking {
    /// Break line only at whitespace, if possible. If we don't find any
    /// whitespace, break words.
    BreakAtWhitespace,
    /// Break words, adding a hyphen before the line-break. Does not use any
    /// smart algorithm, just char-by-char.
    BreakWordsAndInsertHyphen,
    /// Break words char-by-char, don't insert hyphens.
    BreakWordsNoHyphen,
}

#[derive(Copy, Clone)]
pub enum PageBreaking {
    /// Stop after hitting the bottom-right edge of the bounds.
    Cut,
    /// Before stopping at the bottom-right edge, insert ellipsis to signify
    /// more content is available, but only if no hyphen has been inserted yet.
    CutAndInsertEllipsis,
    /// Same as `CutAndInsertEllipsis` but also insert an ellipsis/icon at the
    /// beginning of the next page.
    CutAndInsertEllipsisBoth,
}

/// Visual instructions for laying out a formatted block of text.
#[derive(Copy, Clone)]
pub struct TextLayout {
    /// Bounding box restricting the layout dimensions.
    pub bounds: Rect,

    /// Additional space before beginning of text, can be negative to shift text
    /// upwards.
    pub padding_top: i16,
    /// Additional space between end of text and bottom of bounding box, can be
    /// negative.
    pub padding_bottom: i16,

    /// Fonts, colors, line/page breaking behavior.
    pub style: TextStyle,
    /// Horizontal alignment.
    pub align: Alignment,

    /// Whether to draw "..." (or an icon) at the beginning.
    pub continues_from_prev_page: bool,
}

/// Configuration for chunkifying the text into smaller parts.
#[derive(Copy, Clone)]
pub struct Chunks {
    /// How many characters will be grouped in one chunk.
    pub chunk_size: usize,
    /// How big will be the space between chunks (in pixels).
    pub x_offset: i16,
    /// Maximum amount of rows on one page, if any.
    pub max_rows: Option<usize>,
}

impl Chunks {
    pub const fn new(chunk_size: usize, x_offset: i16) -> Self {
        Chunks {
            chunk_size,
            x_offset,
            max_rows: None,
        }
    }

    pub const fn with_max_rows(mut self, max_rows: usize) -> Self {
        self.max_rows = Some(max_rows);
        self
    }
}

#[derive(Copy, Clone)]
pub struct TextStyle {
    /// Text font ID.
    pub text_font: Font,
    /// Text color.
    pub text_color: Color,
    /// Background color.
    pub background_color: Color,

    /// Foreground color used for drawing the hyphen.
    pub hyphen_color: Color,
    /// Foreground color used for drawing the ellipsis.
    pub ellipsis_color: Color,

    /// Optional icon shown as ellipsis, including its margin from text.
    pub ellipsis_icon: Option<(Icon, i16)>,
    /// Optional icon to signal content continues from previous page,
    /// including text margin.
    pub prev_page_ellipsis_icon: Option<(Icon, i16)>,

    /// Specifies which line-breaking strategy to use.
    pub line_breaking: LineBreaking,
    /// Specifies what to do at the end of the page.
    pub page_breaking: PageBreaking,

    /// Optionally chunkify all the text with a specified chunk
    /// size and pixel offset for the next chunk.
    pub chunks: Option<Chunks>,

    /// Optionally increase the vertical space between text lines
    /// (can be even negative, in which case it will decrease it).
    pub line_spacing: i16,
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
            ellipsis_icon: None,
            prev_page_ellipsis_icon: None,
            line_breaking: LineBreaking::BreakAtWhitespace,
            page_breaking: PageBreaking::CutAndInsertEllipsis,
            chunks: None,
            line_spacing: 0,
        }
    }

    pub const fn with_line_breaking(mut self, line_breaking: LineBreaking) -> Self {
        self.line_breaking = line_breaking;
        self
    }

    pub const fn with_page_breaking(mut self, page_breaking: PageBreaking) -> Self {
        self.page_breaking = page_breaking;
        self
    }

    /// Adding optional icon shown instead of "..." ellipsis.
    pub const fn with_ellipsis_icon(mut self, icon: Icon, margin: i16) -> Self {
        self.ellipsis_icon = Some((icon, margin));
        self
    }

    /// Adding optional icon signalling content continues from previous page.
    pub const fn with_prev_page_icon(mut self, icon: Icon, margin: i16) -> Self {
        self.prev_page_ellipsis_icon = Some((icon, margin));
        self
    }

    /// Adding optional chunkification to the text.
    pub const fn with_chunks(mut self, chunks: Chunks) -> Self {
        self.chunks = Some(chunks);
        self
    }

    /// Adding optional change of vertical line spacing.
    pub const fn with_line_spacing(mut self, line_spacing: i16) -> Self {
        self.line_spacing = line_spacing;
        self
    }

    fn ellipsis_width(&self) -> i16 {
        if let Some((icon, margin)) = self.ellipsis_icon {
            icon.toif.width() + margin
        } else {
            self.text_font.text_width(ELLIPSIS)
        }
    }

    fn prev_page_ellipsis_width(&self) -> i16 {
        if let Some((icon, margin)) = self.prev_page_ellipsis_icon {
            icon.toif.width() + margin
        } else {
            self.text_font.text_width(ELLIPSIS)
        }
    }

    fn prev_page_ellipsis_icon_width(&self) -> i16 {
        if let Some((icon, _)) = self.prev_page_ellipsis_icon {
            icon.toif.width()
        } else {
            0
        }
    }
}

impl TextLayout {
    /// Create a new text layout, with empty size and default text parameters
    /// filled from `T`.
    pub const fn new(style: TextStyle) -> Self {
        Self {
            bounds: Rect::zero(),
            padding_top: 0,
            padding_bottom: 0,
            style,
            align: Alignment::Start,
            continues_from_prev_page: false,
        }
    }

    pub const fn with_bounds(mut self, bounds: Rect) -> Self {
        self.bounds = bounds;
        self
    }

    pub const fn with_align(mut self, align: Alignment) -> Self {
        self.align = align;
        self
    }

    /// Baseline `Point` where we are starting to draw the text.
    pub fn initial_cursor(&self) -> Point {
        let font = &self.style.text_font;
        self.bounds.top_left()
            + Offset::y(font.text_max_height() - font.text_baseline() + self.padding_top)
    }

    /// Trying to fit the content on the current screen.
    pub fn fit_text(&self, text: &str) -> LayoutFit {
        self.layout_text(text, &mut self.initial_cursor(), &mut TextNoOp)
    }

    /// Draw as much text as possible on the current screen.
    pub fn render_text<'s>(&self, text: &str, target: &mut impl Renderer<'s>) -> LayoutFit {
        self.render_text_with_alpha(text, target, 255)
    }
    /// Draw as much text as possible on the current screen.
    pub fn render_text_with_alpha<'s>(
        &self,
        text: &str,
        target: &mut impl Renderer<'s>,
        alpha: u8,
    ) -> LayoutFit {
        self.layout_text(
            text,
            &mut self.initial_cursor(),
            &mut TextRenderer::new(target).with_alpha(alpha),
        )
    }

    /// Loop through the `text` and try to fit it on the current screen,
    /// reporting events to `sink`, which may do something with them (e.g. draw
    /// on screen).
    pub fn layout_text(
        &self,
        text: &str,
        cursor: &mut Point,
        sink: &mut dyn LayoutSink,
    ) -> LayoutFit {
        let init_cursor = *cursor;
        let mut remaining_text = text;
        let mut num_lines = 1;

        // Check if bounding box is high enough for at least one line.
        if cursor.y > self.bottom_y() {
            sink.out_of_bounds();
            return LayoutFit::OutOfBounds {
                processed_chars: 0,
                height: 0,
            };
        }

        // Draw the arrow icon if we are in the middle of a string
        if matches!(
            self.style.page_breaking,
            PageBreaking::CutAndInsertEllipsisBoth
        ) && self.continues_from_prev_page
        {
            // Move the cursor to the right, always the same distance
            // Special case in chunkifying text - move the cursor so that we
            // start with the second chunk.
            if let Some(chunk_config) = self.style.chunks {
                // Showing the arrow at the last chunk position
                // Assuming mono-font, so all the letters have the same width
                let letter_size = self.style.text_font.text_width("a");
                let icon_offset = self.style.prev_page_ellipsis_icon_width() + 2;
                cursor.x += chunk_config.chunk_size as i16 * letter_size - icon_offset;
                sink.prev_page_ellipsis(*cursor, self);
                cursor.x += icon_offset + chunk_config.x_offset;
            } else {
                sink.prev_page_ellipsis(*cursor, self);
                cursor.x += self.style.prev_page_ellipsis_width();
            }
        }

        while !remaining_text.is_empty() {
            let is_last_line = cursor.y + self.style.text_font.line_height() > self.bottom_y();
            let mut force_next_page = false;

            // Check if we have not reached the maximum number of lines we want to draw.
            if let Some(max_rows) = self.style.chunks.and_then(|c| c.max_rows) {
                if num_lines >= max_rows {
                    force_next_page = true;
                }
            }

            let line_ending_space = if is_last_line {
                self.style.ellipsis_width()
            } else {
                0
            };

            let remaining_width = self.bounds.x1 - cursor.x;
            let mut span = Span::fit_horizontally(
                remaining_text,
                remaining_width,
                self.style.text_font,
                self.style.line_breaking,
                line_ending_space,
                self.style.chunks,
            );

            if let Some(chunk_config) = self.style.chunks {
                // Last chunk on the page should not be rendered, put just ellipsis there
                // Chunks is last when the next chunk would not fit on the page horizontally
                let is_last_chunk = (2 * span.advance.x - chunk_config.x_offset) > remaining_width;
                if is_last_line && is_last_chunk && remaining_text.len() > chunk_config.chunk_size {
                    // Making sure no text is rendered here, and that we force a line break
                    span.length = 0;
                    span.advance.x = 2; // To start at the same horizontal line as the chunk itself
                    span.advance.y = self.bounds.y1;
                    span.insert_hyphen_before_line_break = false;
                    span.skip_next_chars = 0;
                }
            }

            cursor.x += match self.align {
                Alignment::Start => 0,
                Alignment::Center => (remaining_width - span.advance.x) / 2,
                Alignment::End => remaining_width - span.advance.x,
            };

            // Report the span at the cursor position.
            // Not doing it when the span length is 0, as that
            // means we encountered a newline/line-break, which we do not draw.
            // Line-breaks are reported later.
            if span.length > 0 {
                sink.text(*cursor, self, &remaining_text[..span.length]);
            }

            // Continue with the rest of the remaining_text.
            remaining_text = &remaining_text[span.length + span.skip_next_chars..];

            // Advance the cursor horizontally.
            cursor.x += span.advance.x;

            if span.advance.y > 0 {
                // We're advancing to the next line.
                num_lines += 1;

                // Possibly making a bigger/smaller vertical jump
                span.advance.y += self.style.line_spacing;

                // Check if we should be appending a hyphen at this point.
                if span.insert_hyphen_before_line_break {
                    sink.hyphen(*cursor, self);
                }
                // Check the amount of vertical space we have left --- or manually force the
                // next page.
                if force_next_page || cursor.y + span.advance.y > self.bottom_y() {
                    // Not enough space on this page.
                    if !remaining_text.is_empty() {
                        // Append ellipsis to indicate more content is available, but only if we
                        // haven't already appended a hyphen.
                        let should_append_ellipsis = matches!(
                            self.style.page_breaking,
                            PageBreaking::CutAndInsertEllipsis
                                | PageBreaking::CutAndInsertEllipsisBoth
                        ) && !span.insert_hyphen_before_line_break;
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

    /// Overall height of the content, including paddings.
    pub fn layout_height(&self, init_cursor: Point, end_cursor: Point) -> i16 {
        self.padding_top
            + self.style.text_font.text_height()
            + (end_cursor.y - init_cursor.y)
            + self.padding_bottom
    }

    /// Y coordinate of the bottom of the available space/bounds
    pub fn bottom_y(&self) -> i16 {
        (self.bounds.y1 - self.padding_bottom).max(self.bounds.y0)
    }
}

impl Dimensions for TextLayout {
    fn fit(&mut self, area: Rect) {
        self.bounds = area;
    }

    fn area(&self) -> Rect {
        self.bounds
    }
}

/// Whether we can fit content on the current screen.
/// Knows how many characters got processed and how high the content is.
#[derive(Clone, Copy, PartialEq, Eq)]
pub enum LayoutFit {
    /// Entire content fits. Vertical size is returned in `height`.
    Fitting { processed_chars: usize, height: i16 },
    /// Content fits partially or not at all.
    OutOfBounds { processed_chars: usize, height: i16 },
}

impl LayoutFit {
    /// How high is the processed/fitted content.
    pub fn height(&self) -> i16 {
        match self {
            LayoutFit::Fitting { height, .. } => *height,
            LayoutFit::OutOfBounds { height, .. } => *height,
        }
    }
}

/// Visitor for text segment operations.
/// Defines responses for certain kind of events encountered
/// when processing the content.
pub trait LayoutSink {
    /// Text should be processed.
    fn text(&mut self, _cursor: Point, _layout: &TextLayout, _text: &str) {}
    /// Hyphen at the end of line.
    fn hyphen(&mut self, _cursor: Point, _layout: &TextLayout) {}
    /// Ellipsis at the end of the page.
    fn ellipsis(&mut self, _cursor: Point, _layout: &TextLayout) {}
    /// Ellipsis at the beginning of the page.
    fn prev_page_ellipsis(&mut self, _cursor: Point, _layout: &TextLayout) {}
    /// Line break - a newline.
    fn line_break(&mut self, _cursor: Point) {}
    /// Content cannot fit on the screen.
    fn out_of_bounds(&mut self) {}
}

/// `LayoutSink` without any functionality.
/// Used to consume events when counting pages
/// or navigating to a certain page number.
pub struct TextNoOp;

impl LayoutSink for TextNoOp {}

pub struct TextRenderer<'a, 's, R>
where
    R: Renderer<'s>,
{
    pub renderer: &'a mut R,
    pd: core::marker::PhantomData<&'s ()>,
    alpha: u8,
}

impl<'a, 's, R> TextRenderer<'a, 's, R>
where
    R: Renderer<'s>,
{
    pub fn new(target: &'a mut R) -> Self {
        Self {
            renderer: target,
            pd: core::marker::PhantomData,
            alpha: 255,
        }
    }

    pub fn with_alpha(self, alpha: u8) -> Self {
        Self { alpha, ..self }
    }
}

impl<'a, 's, R> LayoutSink for TextRenderer<'a, 's, R>
where
    R: Renderer<'s>,
{
    fn text(&mut self, cursor: Point, layout: &TextLayout, text: &str) {
        shape::Text::new(cursor, text, layout.style.text_font)
            .with_fg(layout.style.text_color)
            .with_alpha(self.alpha)
            .render(self.renderer);
    }

    fn hyphen(&mut self, cursor: Point, layout: &TextLayout) {
        shape::Text::new(cursor, "-", layout.style.text_font)
            .with_fg(layout.style.hyphen_color)
            .with_alpha(self.alpha)
            .render(self.renderer);
    }

    fn ellipsis(&mut self, cursor: Point, layout: &TextLayout) {
        if let Some((icon, margin)) = layout.style.ellipsis_icon {
            let bottom_left = cursor + Offset::x(margin);
            shape::ToifImage::new(bottom_left, icon.toif)
                .with_align(Alignment2D::BOTTOM_LEFT)
                .with_fg(layout.style.ellipsis_color)
                .with_alpha(self.alpha)
                .render(self.renderer);
        } else {
            shape::Text::new(cursor, ELLIPSIS, layout.style.text_font)
                .with_fg(layout.style.ellipsis_color)
                .with_alpha(self.alpha)
                .render(self.renderer);
        }
    }

    fn prev_page_ellipsis(&mut self, cursor: Point, layout: &TextLayout) {
        if let Some((icon, _margin)) = layout.style.prev_page_ellipsis_icon {
            shape::ToifImage::new(cursor, icon.toif)
                .with_align(Alignment2D::BOTTOM_LEFT)
                .with_fg(layout.style.ellipsis_color)
                .with_alpha(self.alpha)
                .render(self.renderer);
        } else {
            shape::Text::new(cursor, ELLIPSIS, layout.style.text_font)
                .with_fg(layout.style.ellipsis_color)
                .with_alpha(self.alpha)
                .render(self.renderer);
        }
    }
}

#[cfg(feature = "ui_debug")]
pub mod trace {
    use crate::{trace::ListTracer, ui::geometry::Point};

    use super::*;

    /// `LayoutSink` for debugging purposes.
    pub struct TraceSink<'a>(pub &'a mut dyn ListTracer);

    impl LayoutSink for TraceSink<'_> {
        fn text(&mut self, _cursor: Point, _layout: &TextLayout, text: &str) {
            self.0.string(&text.into());
        }

        fn hyphen(&mut self, _cursor: Point, _layout: &TextLayout) {
            self.0.string(&"-".into());
        }

        fn ellipsis(&mut self, _cursor: Point, _layout: &TextLayout) {
            self.0.string(&ELLIPSIS.into());
        }

        fn prev_page_ellipsis(&mut self, _cursor: Point, _layout: &TextLayout) {
            self.0.string(&ELLIPSIS.into());
        }

        fn line_break(&mut self, _cursor: Point) {
            self.0.string(&"\n".into());
        }
    }
}

/// Carries info about the content that was processed
/// on the current line.
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
    pub fn fit_horizontally(
        text: &str,
        max_width: i16,
        text_font: impl GlyphMetrics,
        breaking: LineBreaking,
        line_ending_space: i16,
        chunks: Option<Chunks>,
    ) -> Self {
        const ASCII_LF: char = '\n';
        const ASCII_CR: char = '\r';
        const ASCII_SPACE: char = ' ';
        const ASCII_HYPHEN: char = '-';

        fn is_whitespace(ch: char) -> bool {
            ch == ASCII_SPACE || ch == ASCII_LF || ch == ASCII_CR
        }

        // Checking if the trimmed text fits the line - the whitespace is not being
        // drawn, so we don't need to account for it.
        let fits_completely = text_font.text_width(text.trim_end()) <= max_width;
        let mut use_hyphens = !matches!(breaking, LineBreaking::BreakWordsNoHyphen);

        // How much space we need to left unused at the end of the line
        // (e.g. for the line-ending hyphen or page-ending ellipsis).
        // Differs for incomplete and complete words (incomplete need
        // to account for a possible hyphen).
        let incomplete_word_end_width = if fits_completely {
            use_hyphens = false;
            0
        } else if line_ending_space > 0 {
            use_hyphens = false;
            line_ending_space
        } else if use_hyphens {
            text_font.char_width(ASCII_HYPHEN)
        } else {
            0
        };
        let complete_word_end_width = if fits_completely {
            0
        } else {
            line_ending_space
        };

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

            // When there is a set chunk size and we reach it,
            // adjust the line advances and return the line.
            if let Some(chunkify_config) = chunks {
                if i == chunkify_config.chunk_size {
                    line.advance.y = 0;
                    line.advance.x += chunkify_config.x_offset;
                    return line;
                }
            }

            // Consider if we could be breaking the line at this position.
            if is_whitespace(ch) && span_width + complete_word_end_width <= max_width {
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
                // Cannot fit on this line. Return the last breakpoint.
                return line;
            } else {
                let have_space_for_break =
                    span_width + char_width + incomplete_word_end_width <= max_width;
                let can_break_word =
                    !matches!(breaking, LineBreaking::BreakAtWhitespace) || !found_any_whitespace;
                if have_space_for_break && can_break_word {
                    // Break after this character, append hyphen.
                    line.length = match char_indices_iter.peek() {
                        Some((idx, _)) => *idx,
                        None => text.len(),
                    };
                    line.advance.x = span_width + char_width;
                    line.insert_hyphen_before_line_break = use_hyphens;
                    line.skip_next_chars = 0;
                }
            }

            span_width += char_width;
        }

        // The whole text is fitting on the current line.
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
        pub width: i16,
        pub height: i16,
    }

    impl GlyphMetrics for Fixed {
        fn char_width(&self, _ch: char) -> i16 {
            self.width
        }

        fn line_height(&self) -> i16 {
            self.height
        }

        fn text_width(&self, text: &str) -> i16 {
            self.width * text.len() as i16
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

    fn spans_from(text: &str, max_width: i16) -> Vec<(&str, bool)> {
        let mut spans = vec![];
        let mut remaining_text = text;
        loop {
            let span = Span::fit_horizontally(
                remaining_text,
                max_width,
                FIXED_FONT,
                LineBreaking::BreakAtWhitespace,
                0,
                None,
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

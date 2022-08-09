//! Mostly copy-pasted stuff from ui/component/text,
//! but with small modifications.
//! It is really mostly changing Op::Text(&'a str) to Op::Text(String<100>),
//! having self.ops as Vec<Op, 30> and changes revolving around it.
//! Even if some stuff could be reused now, I copy-pasted it anyway, as this
//! extension for Icons, Offsets, etc. should no longer live in
//! ui/component/text, and so they can be freely removed (as they are here as
//! well).

use crate::{
    micropython::buffer::StrBuffer,
    ui::{
        display::{self, Color, Font, Icon},
        geometry::{Offset, Point, Rect},
    },
};

use heapless::Vec;

#[derive(Clone)]
pub struct ToDisplay {
    pub text: StrBuffer,
    pub length: usize,
}

impl ToDisplay {
    pub fn new(text: StrBuffer) -> Self {
        Self {
            text: text.clone(),
            length: text.len(),
        }
    }
}

/// Operations that can be done on FormattedText.
#[derive(Clone)]
pub enum Op {
    /// Render text with current color and font.
    Text(ToDisplay),
    /// Render icon.
    /// TODO: make it have `display::Icon`, but it currently has
    /// `T` parameter because of HTC not supporting icons
    Icon(&'static [u8]),
    /// Set current text color.
    Color(Color),
    /// Set currently used font.
    Font(Font),
    /// Set currently used line alignment.
    LineAlignment(LineAlignment),
    /// Move the current cursor by specified Offset.
    CursorOffset(Offset),
    /// Force continuing on the next page.
    NextPage,
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

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum LineAlignment {
    Left,
    Center,
    Right,
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

    /// Fonts, colors, line/page breaking behavior.
    pub style: TextStyle,
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

    /// Specifies how to align text on the line.
    pub line_alignment: LineAlignment,
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
            line_alignment: LineAlignment::Left,
        }
    }
}

impl TextLayout {
    /// Create a new text layout, with empty size and default text parameters
    /// filled from `T`.
    pub fn new(style: TextStyle) -> Self {
        Self {
            bounds: Rect::zero(),
            padding_top: 0,
            padding_bottom: 0,
            style,
        }
    }

    pub fn with_bounds(mut self, bounds: Rect) -> Self {
        self.bounds = bounds;
        self
    }

    /// Baseline `Point` where we are starting to draw the text.
    pub fn initial_cursor(&self) -> Point {
        self.bounds.top_left() + Offset::y(self.style.text_font.text_height() + self.padding_top)
    }

    /// Trying to fit the content on the current screen.
    pub fn fit_text(&self, text: &str) -> LayoutFit {
        self.layout_text(text, &mut self.initial_cursor(), &mut TextNoOp)
    }

    /// Draw as much text as possible on the current screen.
    pub fn render_text(&self, text: &str) {
        self.layout_text(text, &mut self.initial_cursor(), &mut TextRenderer);
    }

    /// Y coordinate of the bottom of the available space/bounds
    pub fn bottom_y(&self) -> i32 {
        (self.bounds.y1 - self.padding_bottom).max(self.bounds.y0)
    }

    /// X coordinate of the right of the available space/bounds
    pub fn right_x(&self) -> i32 {
        self.bounds.x1
    }

    /// Perform some operations defined on `Op` for a list of those `Op`s
    /// - e.g. changing the color, changing the font or rendering the text.
    pub fn layout_ops<const M: usize>(
        mut self,
        ops: Vec<Op, M>,
        cursor: &mut Point,
        skip_bytes: usize,
        sink: &mut dyn LayoutSink,
    ) -> LayoutFit {
        let init_cursor = *cursor;
        let mut total_processed_chars = 0;

        let mut skipped = 0;
        for op in ops {
            let real_op = {
                match op {
                    Op::Text(to_display) if skipped < skip_bytes => {
                        skipped = skipped.saturating_add(to_display.length);
                        if skipped > skip_bytes {
                            let leave_bytes = skipped - skip_bytes;
                            let new_display = ToDisplay {
                                text: to_display.text,
                                length: leave_bytes,
                            };
                            Some(Op::Text(new_display))
                        } else {
                            None
                        }
                    }
                    Op::Icon(_) if skipped < skip_bytes => {
                        // Assume the icon accounts for one character
                        skipped = skipped.saturating_add(1);
                        None
                    }
                    Op::NextPage if skipped < skip_bytes => {
                        // Skip the next page and consider it one character
                        skipped = skipped.saturating_add(1);
                        None
                    }
                    Op::CursorOffset(_) if skipped < skip_bytes => {
                        // Skip any offsets
                        None
                    }
                    op_to_pass_through => Some(op_to_pass_through.clone()),
                }
            };

            if let Some(op) = real_op {
                match op {
                    // Changing color
                    Op::Color(color) => {
                        self.style.text_color = color;
                    }
                    // Changing font
                    Op::Font(font) => {
                        self.style.text_font = font;
                    }
                    // Changing line/text alignment
                    Op::LineAlignment(line_alignment) => {
                        self.style.line_alignment = line_alignment;
                    }
                    // Moving the cursor
                    Op::CursorOffset(offset) => {
                        cursor.x += offset.x;
                        cursor.y += offset.y;
                    }
                    // Moving to the next page
                    Op::NextPage => {
                        // Pretending that nothing more fits on current page to force
                        // continuing on the next one
                        // Making that to account for one character for pagination purposes
                        total_processed_chars += 1;
                        return LayoutFit::OutOfBounds {
                            processed_chars: total_processed_chars,
                            height: self.layout_height(init_cursor, *cursor),
                        };
                    }
                    // Drawing text or icon
                    Op::Text(_) | Op::Icon(_) => {
                        // Text and Icon behave similarly - we try to fit them
                        // on the current page and if they do not fit,
                        // return the appropriate OutOfBounds message
                        let fit = if let Op::Text(to_display) = op {
                            let text = to_display.text.as_ref();
                            let text_len = to_display.length;
                            let start = text.len() - text_len;
                            let to_really_display = &text[start..];
                            // let to_really_display = text.text[text.start..text.end].to_string();
                            self.layout_text(to_really_display, cursor, sink)
                        } else if let Op::Icon(icon) = op {
                            self.layout_icon(icon, cursor, sink)
                        } else {
                            #[cfg(feature = "ui_debug")]
                            panic!("unexpected op type");
                        };

                        match fit {
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
                        }
                    }
                }
            }
        }

        LayoutFit::Fitting {
            processed_chars: total_processed_chars,
            height: self.layout_height(init_cursor, *cursor),
        }
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

        // Check if bounding box is high enough for at least one line.
        if cursor.y > self.bottom_y() {
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
                self.style.text_font,
                self.style.line_breaking,
            );

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

                // Check if we should be appending a hyphen at this point.
                if span.insert_hyphen_before_line_break {
                    sink.hyphen(*cursor, self);
                }
                // Check the amount of vertical space we have left.
                if cursor.y + span.advance.y > self.bottom_y() {
                    if !remaining_text.is_empty() {
                        // Append ellipsis to indicate more content is available, but only if we
                        // haven't already appended a hyphen.
                        let should_append_ellipsis =
                            matches!(self.style.page_breaking, PageBreaking::CutAndInsertEllipsis)
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

    /// Try to fit the `icon` on the current screen
    pub fn layout_icon(
        &self,
        icon: &'static [u8],
        cursor: &mut Point,
        sink: &mut dyn LayoutSink,
    ) -> LayoutFit {
        // Check if bounding box is high enough for at least one line.
        if cursor.y > self.bottom_y() {
            sink.out_of_bounds();
            return LayoutFit::OutOfBounds {
                processed_chars: 0,
                height: 0,
            };
        }

        let icon_obj = Icon::new(icon, "icon");

        // Icon is too wide to fit on current line.
        // Trying to accommodate it on the next line, when it exists on this page.
        if cursor.x + icon_obj.width() > self.right_x() {
            cursor.x = self.bounds.x0;
            cursor.y += self.style.text_font.line_height();
            if cursor.y > self.bottom_y() {
                sink.out_of_bounds();
                return LayoutFit::OutOfBounds {
                    processed_chars: 0,
                    height: self.style.text_font.line_height(),
                };
            }
        }

        sink.icon(*cursor, self, icon_obj);

        // TODO: currently we are using just small icons - that fit nicely to one line -
        // but in case we would do bigger ones, we would need some anti-collision
        // mechanism.

        cursor.x += icon_obj.width() as i32;
        LayoutFit::Fitting {
            // TODO: how to handle this? It could collide with "skip_first_n_bytes"
            processed_chars: 1,
            height: 0, // it should just draw on one line
        }
    }

    /// Overall height of the content, including paddings.
    fn layout_height(&self, init_cursor: Point, end_cursor: Point) -> i32 {
        self.padding_top
            + self.style.text_font.text_height()
            + (end_cursor.y - init_cursor.y)
            + self.padding_bottom
    }
}

/// Whether we can fit content on the current screen.
/// Knows how many characters got processed and how high the content is.
pub enum LayoutFit {
    /// Entire content fits. Vertical size is returned in `height`.
    Fitting { processed_chars: usize, height: i32 },
    /// Content fits partially or not at all.
    OutOfBounds { processed_chars: usize, height: i32 },
}

impl LayoutFit {
    /// How high is the processed/fitted content.
    pub fn height(&self) -> i32 {
        match self {
            LayoutFit::Fitting { height, .. } => *height,
            LayoutFit::OutOfBounds { height, .. } => *height,
        }
    }
}

// TODO: LayoutSink could support even things like drawing icons
// or making custom x or y offsets from any position

/// Visitor for text segment operations.
/// Defines responses for certain kind of events encountered
/// when processing the content.
pub trait LayoutSink {
    /// Text should be processed.
    fn text(&mut self, _cursor: Point, _layout: &TextLayout, _text: &str) {}
    /// Text should be processed.
    fn icon(&mut self, _cursor: Point, _layout: &TextLayout, _icon: Icon<&'static str>) {}
    /// Hyphen at the end of line.
    fn hyphen(&mut self, _cursor: Point, _layout: &TextLayout) {}
    /// Ellipsis at the end of the page.
    fn ellipsis(&mut self, _cursor: Point, _layout: &TextLayout) {}
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

/// `LayoutSink` for rendering the content.
pub struct TextRenderer;

impl LayoutSink for TextRenderer {
    fn text(&mut self, cursor: Point, layout: &TextLayout, text: &str) {
        // Accounting for the line-alignment - left, right or center.
        // Assume the current line can be drawn on from the cursor
        // to the right side of the screen.

        match layout.style.line_alignment {
            LineAlignment::Left => {
                display::text(
                    cursor,
                    text,
                    layout.style.text_font,
                    layout.style.text_color,
                    layout.style.background_color,
                );
            }
            LineAlignment::Center => {
                let center = Point::new(cursor.x + (layout.bounds.x1 - cursor.x) / 2, cursor.y);
                display::text_center(
                    center,
                    text,
                    layout.style.text_font,
                    layout.style.text_color,
                    layout.style.background_color,
                );
            }
            LineAlignment::Right => {
                let right = Point::new(layout.bounds.x1, cursor.y);
                display::text_right(
                    right,
                    text,
                    layout.style.text_font,
                    layout.style.text_color,
                    layout.style.background_color,
                );
            }
        }
    }

    fn hyphen(&mut self, cursor: Point, layout: &TextLayout) {
        display::text(
            cursor,
            "-",
            layout.style.text_font,
            layout.style.hyphen_color,
            layout.style.background_color,
        );
    }

    fn ellipsis(&mut self, cursor: Point, layout: &TextLayout) {
        display::text(
            cursor,
            "...",
            layout.style.text_font,
            layout.style.ellipsis_color,
            layout.style.background_color,
        );
    }

    fn icon(&mut self, cursor: Point, layout: &TextLayout, icon: Icon<&'static str>) {
        icon.draw_bottom_left(
            cursor,
            layout.style.text_color,
            layout.style.background_color,
        );
    }
}

pub trait GlyphMetrics {
    fn char_width(&self, ch: char) -> i32;
    fn line_height(&self) -> i32;
}

impl GlyphMetrics for Font {
    fn char_width(&self, ch: char) -> i32 {
        Font::char_width(*self, ch)
    }

    fn line_height(&self) -> i32 {
        Font::line_height(*self)
    }
}

/// Carries info about the content that was processed
/// on the current line.
#[derive(Debug, PartialEq, Eq)]
pub struct Span {
    /// How many characters from the input text this span is laying out.
    pub length: usize,
    /// How many chars from the input text should we skip before fitting the
    /// next span?
    pub skip_next_chars: usize,
    /// By how much to offset the cursor after this span. If the vertical offset
    /// is bigger than zero, it means we are breaking the line.
    pub advance: Offset,
    /// If we are breaking the line, should we insert a hyphen right after this
    /// span to indicate a word-break?
    pub insert_hyphen_before_line_break: bool,
}

impl Span {
    fn fit_horizontally(
        text: &str,
        max_width: i32,
        text_font: impl GlyphMetrics,
        breaking: LineBreaking,
    ) -> Self {
        const ASCII_LF: char = '\n';
        const ASCII_CR: char = '\r';
        const ASCII_SPACE: char = ' ';
        const ASCII_HYPHEN: char = '-';

        fn is_whitespace(ch: char) -> bool {
            ch == ASCII_SPACE || ch == ASCII_LF || ch == ASCII_CR
        }

        let hyphen_width = text_font.char_width(ASCII_HYPHEN);

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
                // Cannot fit on this line. Return the last breakpoint.
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

        // The whole text is fitting on the current line.
        Self {
            length: text.len(),
            advance: Offset::x(span_width),
            insert_hyphen_before_line_break: false,
            skip_next_chars: 0,
        }
    }
}

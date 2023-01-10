//! Mostly extending TextLayout from ui/component/text/layout.rs
//! (support for more Ops like icon drawing or arbitrary offsets)
//! - unfortunately means there is quite a lot of duplication at the
//! benefit of not polluting the original code things not used there
//! (icons, QR codes)
//!
//! TODO: CONSIDERATION:
//! A) maintain this little dirty state
//!    - biggest duplications are in `layout_text`, which needed to be
//!      completely copied and renamed to `layout_text_new` just to use the new
//!      `Sink` here, which supports the icon and QR code
//! B) move all the new code into ui/component/text/layout.rs
//!    - would mean moving there QrCodeInfo, Sink::QrCode, Sink::Icon, etc.
//! My preference is B, but we need to agree on that

use crate::{
    micropython::buffer::StrBuffer,
    ui::{
        component::{
            text::layout::{LayoutFit, Span},
            PageBreaking, TextLayout,
        },
        display::{self, Color, Font, Icon},
        geometry::{Alignment, Offset, Point},
    },
};

use heapless::Vec;

/// To account for operations that are not made of characters
/// but need to be accounted for somehow.
/// Number of processed characters will be increased by this
/// to account for the operation.
const PROCESSED_CHARS_ONE: usize = 1;

/// Container for text allowing for its displaying by chunks
/// without the need to allocate a new String each time.
#[derive(Clone)]
pub struct ToDisplay {
    pub text: StrBuffer,
    pub length_from_end: usize,
}

impl ToDisplay {
    pub fn new(text: StrBuffer) -> Self {
        Self {
            text,
            length_from_end: text.len(),
        }
    }
}

/// Holding information about a QR code to be displayed.
#[derive(Clone)]
pub struct QrCodeInfo {
    pub data: StrBuffer,
    pub max_size: i16,
    pub case_sensitive: bool,
    pub center: Point,
}

impl QrCodeInfo {
    pub fn new(data: StrBuffer, max_size: i16, case_sensitive: bool, center: Point) -> Self {
        Self {
            data,
            max_size,
            case_sensitive,
            center,
        }
    }
}

/// Operations that can be done on the screen.
#[derive(Clone)]
pub enum Op {
    /// Render text with current color and font.
    Text(ToDisplay),
    /// Render icon.
    Icon(Icon),
    /// Render QR Code.
    QrCode(QrCodeInfo),
    /// Set current text color.
    Color(Color),
    /// Set currently used font.
    Font(Font),
    /// Set currently used line alignment.
    Alignment(Alignment),
    /// Move the current cursor by specified Offset.
    CursorOffset(Offset),
    /// Force continuing on the next page.
    NextPage,
}

impl TextLayout {
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

        // TODO: get cursor at the very top of the page and only then subtract
        // the font height according to the CURRENT font - which can be different
        // from the original font.

        let mut skipped = 0;
        for op in ops {
            let real_op = {
                match op {
                    Op::Text(to_display) if skipped < skip_bytes => {
                        skipped = skipped.saturating_add(to_display.length_from_end);
                        if skipped > skip_bytes {
                            let leave_bytes = skipped - skip_bytes;
                            let new_display = ToDisplay {
                                text: to_display.text,
                                length_from_end: leave_bytes,
                            };
                            Some(Op::Text(new_display))
                        } else {
                            None
                        }
                    }
                    Op::Icon(_) if skipped < skip_bytes => {
                        skipped = skipped.saturating_add(PROCESSED_CHARS_ONE);
                        None
                    }
                    Op::QrCode(_) if skipped < skip_bytes => {
                        skipped = skipped.saturating_add(PROCESSED_CHARS_ONE);
                        None
                    }
                    Op::NextPage if skipped < skip_bytes => {
                        skipped = skipped.saturating_add(PROCESSED_CHARS_ONE);
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
                    Op::Alignment(line_alignment) => {
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
                        total_processed_chars += PROCESSED_CHARS_ONE;
                        return LayoutFit::OutOfBounds {
                            processed_chars: total_processed_chars,
                            height: self.layout_height(init_cursor, *cursor),
                        };
                    }
                    Op::QrCode(qr_details) => {
                        self.layout_qr_code(qr_details, sink);
                        // QR codes are always the last component that can be shown
                        // on the given page (meaning a series of Op's).
                        // Throwing Fitting to force the end of the whole page.
                        // (It would be too complicated to account for it by modifying cursor, etc.,
                        // and there is not a need for it currently. If we want QR code together
                        // with some other things on the same screen, just first render the other
                        // things and do the QR code last.)
                        total_processed_chars += PROCESSED_CHARS_ONE;
                        return LayoutFit::Fitting {
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
                            // TODO: document this a little bit
                            let text = to_display.text.as_ref();
                            let text_len = to_display.length_from_end;
                            let start = text.len() - text_len;
                            let to_really_display = &text[start..];
                            // TODO: pass in whether we are in the middle of a string
                            // (start > 0),
                            // in which case we could/should start the text with
                            // an arrow icon (opposite to ellipsis)
                            self.layout_text_new(to_really_display, cursor, sink)
                        } else if let Op::Icon(icon) = op {
                            self.layout_icon(icon, cursor, sink)
                        } else {
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
    pub fn layout_text_new(
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

        // TODO: draw the arrow icon if we are in the middle of a string

        // TODO: have the variable `is_last` and in that case tell it to
        // `fit_horizontally`, which will then account for the ellipsis icon
        // instead of the hyphen (have it `ellipsis_length`)

        while !remaining_text.is_empty() {
            let remaining_width = self.bounds.x1 - cursor.x;
            let span = Span::fit_horizontally(
                remaining_text,
                remaining_width,
                self.style.text_font,
                self.style.line_breaking,
            );

            cursor.x += match self.align {
                Alignment::Start => 0,
                Alignment::Center => (remaining_width - span.advance.x) / 2,
                Alignment::End => remaining_width - span.advance.x,
            };

            // Report the span at the cursor position.
            // Not doing it when the span length is 0, as that
            // means we encountered a newline/line-break, which we do not draw.
            // Line-breaks are reported later.
            let text_to_display = &remaining_text[..span.length];
            if span.length > 0 {
                sink.text(*cursor, self, text_to_display);
            }
            let last_displayed_char = text_to_display.chars().last().unwrap_or('\n');

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
                    // Not enough space on this page.
                    if !remaining_text.is_empty() {
                        // Append ellipsis to indicate more content is available, but only if we
                        // haven't already appended a hyphen. Also not doing it if the last
                        // character is a dot (signalling end of one sentence).
                        let should_append_ellipsis =
                            matches!(self.style.page_breaking, PageBreaking::CutAndInsertEllipsis)
                                && !span.insert_hyphen_before_line_break
                                && last_displayed_char != '.';
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
        icon: Icon,
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

        // Icon is too wide to fit on current line.
        // Trying to accommodate it on the next line, when it exists on this page.
        if cursor.x + icon.width() > self.bounds.x1 {
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

        sink.icon(*cursor, self, icon);

        cursor.x += icon.width() as i16;
        LayoutFit::Fitting {
            processed_chars: PROCESSED_CHARS_ONE,
            height: 0, // it should just draw on one line
        }
    }

    /// Fitting the QR code on the current screen.
    /// Not returning `LayoutFit`, QR codes are handled differently,
    /// they automatically throw out of bounds.
    pub fn layout_qr_code(&self, qr_code_info: QrCodeInfo, sink: &mut dyn LayoutSink) {
        sink.qrcode(qr_code_info);
    }
}

/// Visitor for text segment operations.
/// Defines responses for certain kind of events encountered
/// when processing the content.
pub trait LayoutSink {
    /// Text should be processed.
    fn text(&mut self, _cursor: Point, _layout: &TextLayout, _text: &str) {}
    /// Icon should be displayed.
    fn icon(&mut self, _cursor: Point, _layout: &TextLayout, _icon: Icon) {}
    /// QR code should be displayed.
    fn qrcode(&mut self, _qr_code: QrCodeInfo) {}
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
            Alignment::Start => {
                display::text_left(
                    cursor,
                    text,
                    layout.style.text_font,
                    layout.style.text_color,
                    layout.style.background_color,
                );
            }
            Alignment::Center => {
                let center = Point::new(cursor.x + (layout.bounds.x1 - cursor.x) / 2, cursor.y);
                display::text_center(
                    center,
                    text,
                    layout.style.text_font,
                    layout.style.text_color,
                    layout.style.background_color,
                );
            }
            Alignment::End => {
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
        display::text_left(
            cursor,
            "-",
            layout.style.text_font,
            layout.style.hyphen_color,
            layout.style.background_color,
        );
    }

    fn ellipsis(&mut self, cursor: Point, layout: &TextLayout) {
        if let Some(icon) = layout.style.ellipsis_icon {
            // Icon should end little below the cursor's baseline
            // TODO: add some offset to the right
            let bottom_left = cursor + Offset::y(2);
            display::icon_bottom_left(
                bottom_left,
                icon,
                layout.style.ellipsis_color,
                layout.style.background_color,
            );
        } else {
            display::text_left(
                cursor,
                "...",
                layout.style.text_font,
                layout.style.ellipsis_color,
                layout.style.background_color,
            );
        }
    }

    fn icon(&mut self, cursor: Point, layout: &TextLayout, icon: Icon) {
        icon.draw_bottom_left(
            cursor,
            layout.style.text_color,
            layout.style.background_color,
        );
    }

    fn qrcode(&mut self, qr_code: QrCodeInfo) {
        display::qrcode(
            qr_code.center,
            qr_code.data.as_ref(),
            qr_code.max_size as _,
            qr_code.case_sensitive,
        )
        .unwrap_or(())
    }
}

/// `LayoutSink` for debugging purposes.
#[cfg(feature = "ui_debug")]
pub struct TraceSink<'a>(pub &'a mut dyn crate::trace::Tracer);

#[cfg(feature = "ui_debug")]
use crate::trace::Trace;

#[cfg(feature = "ui_debug")]
impl<'a> LayoutSink for TraceSink<'a> {
    fn text(&mut self, _cursor: Point, _layout: &TextLayout, text: &str) {
        self.0.string(text);
    }

    fn icon(&mut self, _cursor: Point, _layout: &TextLayout, icon: Icon) {
        icon.trace(self.0);
    }

    fn qrcode(&mut self, qr_code: QrCodeInfo) {
        self.0.string("QR code: ");
        self.0.string(qr_code.data.as_ref());
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

//! Mostly extending TextLayout from ui/component/text/layout.rs
//! (support for more Ops like alignments or arbitrary offsets)

use crate::{
    micropython::buffer::StrBuffer,
    ui::{
        component::{
            text::layout::{LayoutFit, LayoutSink, QrCodeInfo},
            TextLayout,
        },
        display::{Color, Font},
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

/// Operations that can be done on the screen.
#[derive(Clone)]
pub enum Op {
    /// Render text with current color and font.
    Text(ToDisplay),
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
    pub fn layout_ops_new<const M: usize>(
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
                        self.align = line_alignment;
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
                    Op::Text(to_display) => {
                        // Try to fit text on the current page and if they do not fit,
                        // return the appropriate OutOfBounds message
                        // TODO: document this a little bit
                        let text = to_display.text.as_ref();
                        let text_len = to_display.length_from_end;
                        let start = text.len() - text_len;
                        let to_really_display = &text[start..];
                        let fit = self.layout_text(to_really_display, cursor, sink);

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

    /// Fitting the QR code on the current screen.
    /// Not returning `LayoutFit`, QR codes are handled differently,
    /// they automatically throw out of bounds.
    pub fn layout_qr_code(&self, qr_code_info: QrCodeInfo, sink: &mut dyn LayoutSink) {
        sink.qrcode(qr_code_info);
    }
}

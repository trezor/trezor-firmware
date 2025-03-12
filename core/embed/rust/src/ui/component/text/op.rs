use crate::{
    strutil::TString,
    ui::{
        display::{Color, Font},
        geometry::{Alignment, Offset, Rect},
        util::ResultExt,
    },
};

use super::{
    layout::{Chunks, LayoutFit, LayoutSink, TextLayout},
    LineBreaking, TextStyle,
};

use heapless::Vec;

// So that there is only one implementation, and not multiple generic ones
// as would be via `const N: usize` generics.
const MAX_OPS: usize = 20;

/// To account for operations that are not made of characters
/// but need to be accounted for somehow.
/// Number of processed characters will be increased by this
/// to account for the operation.
const PROCESSED_CHARS_ONE: usize = 1;

#[derive(Clone)]
/// Extension of TextLayout, allowing for Op-based operations
pub struct OpTextLayout<'a> {
    pub layout: TextLayout,
    ops: Vec<Op<'a>, MAX_OPS>,
}

impl<'a> OpTextLayout<'a> {
    pub fn new(style: TextStyle) -> Self {
        Self {
            layout: TextLayout::new(style),
            ops: Vec::new(),
        }
    }

    pub fn is_empty(&self) -> bool {
        self.ops.len() == 0
    }

    pub fn place(&mut self, bounds: Rect) -> Rect {
        self.layout.bounds = bounds;
        bounds
    }

    /// Send the layout's content into a sink.
    pub fn layout_content(&mut self, skip_bytes: usize, sink: &mut dyn LayoutSink) -> LayoutFit {
        self.layout_ops(skip_bytes, Offset::zero(), sink)
    }

    /// Perform some operations defined on `Op` for a list of those `Op`s
    /// - e.g. changing the color, changing the font or rendering the text.
    pub fn layout_ops(
        &self,
        skip_bytes: usize,
        offset: Offset,
        sink: &mut dyn LayoutSink,
    ) -> LayoutFit {
        // TODO: make sure it is called when we have the current font (not sooner)
        let cursor = &mut (self.layout.initial_cursor() + offset);
        let init_cursor = *cursor;
        let mut total_processed_chars = 0;
        let mut layout = self.layout;

        // Do something when it was not skipped
        for op in Self::filter_skipped_ops(self.ops.iter(), skip_bytes) {
            match op {
                // Changing color
                Op::Color(color) => {
                    layout.style.text_color = color;
                }
                // Changing font
                Op::Font(font) => {
                    layout.style.text_font = font;
                }
                // Changing line/text alignment
                Op::Alignment(line_alignment) => {
                    layout.align = line_alignment;
                }
                // Changing line breaking
                Op::LineBreaking(line_breaking) => {
                    layout.style.line_breaking = line_breaking;
                }
                // Moving the cursor
                Op::CursorOffset(offset) => {
                    cursor.x += offset.x;
                    cursor.y += offset.y;
                }
                Op::Chunkify(chunks) => {
                    layout.style.chunks = chunks;
                }
                Op::LineSpacing(line_spacing) => {
                    layout.style.line_spacing = line_spacing;
                }
                // Moving to the next page
                Op::NextPage => {
                    // Pretending that nothing more fits on current page to force
                    // continuing on the next one
                    total_processed_chars += PROCESSED_CHARS_ONE;
                    return LayoutFit::OutOfBounds {
                        processed_chars: total_processed_chars,
                        height: layout.layout_height(init_cursor, *cursor),
                    };
                }
                // Drawing text
                Op::Text(text, font, continued) => {
                    // Try to fit text on the current page and if they do not fit,
                    // return the appropriate OutOfBounds message

                    // Inserting the ellipsis at the very beginning of the text if needed
                    // (just for incomplete texts that were separated)
                    layout.continues_from_prev_page = continued;
                    layout.style.text_font = font;

                    let fit = text.map(|t| layout.layout_text(t, cursor, sink));

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
                                height: layout.layout_height(init_cursor, *cursor),
                            };
                        }
                    }
                }
            }
        }

        LayoutFit::Fitting {
            processed_chars: total_processed_chars,
            height: layout.layout_height(init_cursor, *cursor),
        }
    }

    /// Gets rid of all action-Ops that are before the `skip_bytes` threshold.
    /// (Not removing the style changes, e.g. Font or Color, because they need
    /// to be correctly set for future Text operations.)
    fn filter_skipped_ops<'b, I>(
        ops_iter: I,
        skip_bytes: usize,
    ) -> impl Iterator<Item = Op<'a>> + 'b
    where
        I: Iterator<Item = &'b Op<'a>> + 'b,
        'a: 'b,
    {
        let mut skipped = 0;
        ops_iter.filter_map(move |op| {
            match op {
                Op::Text(text, font, _continued) if skipped < skip_bytes => {
                    let skip_text_bytes_if_fits_partially = skip_bytes - skipped;
                    skipped = skipped.saturating_add(text.len());
                    if skipped > skip_bytes {
                        // Fits partially
                        // Skipping some bytes at the beginning, leaving rest
                        // Signifying that the text continues from previous page
                        Some(Op::Text(
                            text.skip_prefix(skip_text_bytes_if_fits_partially),
                            font,
                            true,
                        ))
                    } else {
                        // Does not fit at all
                        None
                    }
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
        })
    }
}

// Op-adding operations
impl<'a> OpTextLayout<'a> {
    pub fn with_new_item(mut self, item: Op<'a>) -> Self {
        self.ops
            .push(item)
            .assert_if_debugging_ui("Could not push to self.ops - increase MAX_OPS.");
        self
    }

    pub fn text(self, text: impl Into<TString<'a>>, font: Font) -> Self {
        self.with_new_item(Op::Text(text.into(), font, false))
    }

    pub fn newline(self) -> Self {
        let font = self.layout.style.text_font;
        self.text("\n", font)
    }

    pub fn newline_half(self) -> Self {
        let font = self.layout.style.text_font;
        self.text("\r", font)
    }

    pub fn next_page(self) -> Self {
        self.with_new_item(Op::NextPage)
    }

    pub fn offset(self, offset: Offset) -> Self {
        self.with_new_item(Op::CursorOffset(offset))
    }

    pub fn alignment(self, alignment: Alignment) -> Self {
        self.with_new_item(Op::Alignment(alignment))
    }

    pub fn line_breaking(self, line_breaking: LineBreaking) -> Self {
        self.with_new_item(Op::LineBreaking(line_breaking))
    }

    pub fn chunks(self, chunks: Option<Chunks>) -> Self {
        self.with_new_item(Op::Chunkify(chunks))
    }

    pub fn line_spacing(self, spacing: i16) -> Self {
        self.with_new_item(Op::LineSpacing(spacing))
    }

    pub fn chunkify_text(self, chunks: Option<(Chunks, i16)>) -> Self {
        if let Some(chunks) = chunks {
            self.chunks(Some(chunks.0)).line_spacing(chunks.1)
        } else {
            self.chunks(None).line_spacing(0)
        }
    }
}

#[derive(Clone)]
pub enum Op<'a> {
    /// Render text with current color and specified font.
    /// Bool signifies whether this is a split Text Op continued from previous
    /// page. If true, a leading ellipsis will be rendered.
    Text(TString<'a>, Font, bool),
    /// Set current text color.
    Color(Color),
    /// Set currently used font.
    Font(Font),
    /// Set currently used line alignment.
    Alignment(Alignment),
    /// Set currently used line breaking algorithm.
    LineBreaking(LineBreaking),
    /// Move the current cursor by specified Offset.
    CursorOffset(Offset),
    /// Force continuing on the next page.
    NextPage,
    /// Render the following text in a chunkified way. None will disable that.
    Chunkify(Option<Chunks>),
    /// Change the line vertical line spacing.
    LineSpacing(i16),
}

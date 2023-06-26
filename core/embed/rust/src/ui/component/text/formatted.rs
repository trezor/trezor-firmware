use crate::{
    strutil::StringType,
    ui::{
        component::{Component, Event, EventCtx, Never, Paginate},
        geometry::{Alignment, Offset, Rect},
    },
};

use super::{
    layout::{LayoutFit, LayoutSink, TextNoOp, TextRenderer},
    op::OpTextLayout,
};

#[derive(Clone)]
pub struct FormattedText<T: StringType + Clone> {
    op_layout: OpTextLayout<T>,
    vertical: Alignment,
    char_offset: usize,
    y_offset: i16,
}

impl<T: StringType + Clone> FormattedText<T> {
    pub fn new(op_layout: OpTextLayout<T>) -> Self {
        Self {
            op_layout,
            vertical: Alignment::Start,
            char_offset: 0,
            y_offset: 0,
        }
    }

    pub fn vertically_centered(mut self) -> Self {
        self.vertical = Alignment::Center;
        self
    }

    fn layout_content(&mut self, sink: &mut dyn LayoutSink) -> LayoutFit {
        self.op_layout
            .layout_ops(self.char_offset, Offset::y(self.y_offset), sink)
    }

    fn align_vertically(&mut self, content_height: i16) {
        let bounds_height = self.op_layout.layout.bounds.height();
        if content_height >= bounds_height {
            self.y_offset = 0;
            return;
        }
        self.y_offset = match self.vertical {
            Alignment::Start => 0,
            Alignment::Center => (bounds_height - content_height) / 2,
            Alignment::End => bounds_height - content_height,
        }
    }
}

// Pagination
impl<T: StringType + Clone> Paginate for FormattedText<T> {
    fn page_count(&mut self) -> usize {
        let mut page_count = 1; // There's always at least one page.

        // Make sure we're starting page counting from the very beginning
        // (but remembering the offsets not to change them).
        let initial_y_offset = self.y_offset;
        let initial_char_offset = self.char_offset;
        self.char_offset = 0;
        self.y_offset = 0;

        // Looping through the content and counting pages
        // until we finally fit.
        loop {
            let fit = self.layout_content(&mut TextNoOp);
            match fit {
                LayoutFit::Fitting { .. } => {
                    break;
                }
                LayoutFit::OutOfBounds {
                    processed_chars, ..
                } => {
                    page_count += 1;
                    self.char_offset += processed_chars;
                }
            }
        }

        // Setting the offsets back to the initial values.
        self.char_offset = initial_char_offset;
        self.y_offset = initial_y_offset;

        page_count
    }

    fn change_page(&mut self, to_page: usize) {
        let mut active_page = 0;

        // Make sure we're starting from the beginning.
        self.char_offset = 0;
        self.y_offset = 0;

        // Looping through the content until we arrive at
        // the wanted page.
        let mut fit = self.layout_content(&mut TextNoOp);
        while active_page < to_page {
            match fit {
                LayoutFit::Fitting { .. } => {
                    break;
                }
                LayoutFit::OutOfBounds {
                    processed_chars, ..
                } => {
                    active_page += 1;
                    self.char_offset += processed_chars;
                    fit = self.layout_content(&mut TextNoOp);
                }
            }
        }
        // Setting appropriate self.y_offset
        self.align_vertically(fit.height());
    }
}

impl<T: StringType + Clone> Component for FormattedText<T> {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.op_layout.place(bounds);
        let height = self.layout_content(&mut TextNoOp).height();
        self.align_vertically(height);
        bounds
    }

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    fn paint(&mut self) {
        self.layout_content(&mut TextRenderer);
    }

    #[cfg(feature = "ui_bounds")]
    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        sink(self.op_layout.layout.bounds)
    }
}

// DEBUG-ONLY SECTION BELOW

#[cfg(feature = "ui_debug")]
impl<T: StringType + Clone> FormattedText<T> {
    /// Is the same as layout_content, but does not use `&mut self`
    /// to be compatible with `trace`.
    /// Therefore it has to do the `clone` of `op_layout`.
    pub fn layout_content_debug(&self, sink: &mut dyn LayoutSink) -> LayoutFit {
        // TODO: how to solve it "properly", without the `clone`?
        // (changing `trace` to `&mut self` had some other isses...)
        self.op_layout
            .clone()
            .layout_content(self.char_offset, sink)
    }
}

#[cfg(feature = "ui_debug")]
impl<T: StringType + Clone> crate::trace::Trace for FormattedText<T> {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        use crate::ui::component::text::layout::trace::TraceSink;
        use core::cell::Cell;
        let fit: Cell<Option<LayoutFit>> = Cell::new(None);
        t.component("FormattedText");
        t.in_list("text", &|l| {
            let result = self.layout_content_debug(&mut TraceSink(l));
            fit.set(Some(result));
        });
        t.bool("fits", matches!(fit.get(), Some(LayoutFit::Fitting { .. })));
    }
}

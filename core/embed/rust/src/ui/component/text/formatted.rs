use crate::{
    strutil::StringType,
    ui::{
        component::{Component, Event, EventCtx, Never, Paginate},
        geometry::Rect,
    },
};

use super::{
    layout::{LayoutFit, LayoutSink, TextNoOp, TextRenderer},
    op::OpTextLayout,
};

#[derive(Clone)]
pub struct FormattedText<T: StringType + Clone> {
    op_layout: OpTextLayout<T>,
    char_offset: usize,
}

impl<T: StringType + Clone> FormattedText<T> {
    pub fn new(op_layout: OpTextLayout<T>) -> Self {
        Self {
            op_layout,
            char_offset: 0,
        }
    }

    fn layout_content(&mut self, sink: &mut dyn LayoutSink) -> LayoutFit {
        self.op_layout.layout_content(self.char_offset, sink)
    }
}

// Pagination
impl<T: StringType + Clone> Paginate for FormattedText<T> {
    fn page_count(&mut self) -> usize {
        let mut page_count = 1; // There's always at least one page.
        let mut char_offset = 0;

        // Make sure we're starting from the beginning.
        self.char_offset = char_offset;

        // Looping through the content and counting pages
        // until we finally fit.
        loop {
            let fit = self.layout_content(&mut TextNoOp);
            match fit {
                LayoutFit::Fitting { .. } => {
                    break; // TODO: We should consider if there's more content
                           // to render.
                }
                LayoutFit::OutOfBounds {
                    processed_chars, ..
                } => {
                    page_count += 1;
                    char_offset += processed_chars;
                    self.char_offset = char_offset;
                }
            }
        }

        // Reset the char offset back to the beginning.
        self.char_offset = 0;

        page_count
    }

    fn change_page(&mut self, to_page: usize) {
        let mut active_page = 0;
        let mut char_offset = 0;

        // Make sure we're starting from the beginning.
        self.char_offset = char_offset;

        // Looping through the content until we arrive at
        // the wanted page.
        while active_page < to_page {
            let fit = self.layout_content(&mut TextNoOp);
            match fit {
                LayoutFit::Fitting { .. } => {
                    break; // TODO: We should consider if there's more content
                           // to render.
                }
                LayoutFit::OutOfBounds {
                    processed_chars, ..
                } => {
                    active_page += 1;
                    char_offset += processed_chars;
                    self.char_offset = char_offset;
                }
            }
        }
    }
}

impl<T: StringType + Clone> Component for FormattedText<T> {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.op_layout.place(bounds);
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

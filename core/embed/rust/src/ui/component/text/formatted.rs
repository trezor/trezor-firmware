use crate::ui::{
    component::{Component, Event, EventCtx, Never, PaginateFull},
    geometry::{Alignment, Offset, Rect},
    shape::Renderer,
    util::Pager,
};

use super::{
    layout::{LayoutFit, LayoutSink, TextNoOp, TextRenderer},
    op::OpTextLayout,
};

#[derive(Clone)]
pub struct FormattedText {
    op_layout: OpTextLayout<'static>,
    vertical: Alignment,
    char_offset: usize,
    y_offset: i16,
    pager: Pager,
}

impl FormattedText {
    pub fn new(op_layout: OpTextLayout<'static>) -> Self {
        Self {
            op_layout,
            vertical: Alignment::Start,
            char_offset: 0,
            y_offset: 0,
            pager: Pager::single_page(),
        }
    }

    pub fn vertically_centered(mut self) -> Self {
        self.vertical = Alignment::Center;
        self
    }

    fn layout_content(&self, sink: &mut dyn LayoutSink) -> LayoutFit {
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

    #[cfg(feature = "ui_debug")]
    pub(crate) fn trace_lines_as_list(&self, l: &mut dyn crate::trace::ListTracer) -> LayoutFit {
        use crate::ui::component::text::layout::trace::TraceSink;
        let result = self.layout_content(&mut TraceSink(l));
        result
    }
}

// Pagination
impl PaginateFull for FormattedText {
    fn pager(&self) -> Pager {
        self.pager
    }

    fn change_page(&mut self, to_page: u16) {
        let to_page = to_page.min(self.pager.total() - 1);

        // reset current position if needed and calculate how many pages forward we need
        // to go
        self.y_offset = 0;
        let mut pages_remaining = if to_page < self.pager.current() {
            self.char_offset = 0;
            to_page
        } else {
            to_page - self.pager.current()
        };

        // move forward until we arrive at the wanted page
        let mut fit = self.layout_content(&mut TextNoOp);
        while pages_remaining > 0 {
            match fit {
                LayoutFit::Fitting { .. } => {
                    break;
                }
                LayoutFit::OutOfBounds {
                    processed_chars, ..
                } => {
                    pages_remaining -= 1;
                    self.char_offset += processed_chars;
                    fit = self.layout_content(&mut TextNoOp);
                }
            }
        }
        // Setting appropriate self.y_offset
        self.align_vertically(fit.height());
        // Update the pager
        self.pager.set_current(to_page);
    }
}

impl Component for FormattedText {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        if self.op_layout.layout.bounds == bounds {
            // Skip placement logic (and resetting pager) if the bounds haven't changed.
            return bounds;
        }

        self.op_layout.place(bounds);

        // reset current position
        self.char_offset = 0;
        self.y_offset = 0;

        let mut page_count = 1; // There's always at least one page.
        let mut first_fit = None;

        // Looping through the content and counting pages until we finally fit.
        loop {
            let fit = self.layout_content(&mut TextNoOp);
            first_fit.get_or_insert(fit);
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

        // reset position to start
        self.char_offset = 0;
        // align vertically and set pager
        let first_fit = unwrap!(first_fit);
        self.align_vertically(first_fit.height());
        self.pager = Pager::new(page_count);

        bounds
    }

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.layout_content(&mut TextRenderer::new(target));
    }
}

// DEBUG-ONLY SECTION BELOW

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for FormattedText {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        use core::cell::Cell;
        let fit: Cell<Option<LayoutFit>> = Cell::new(None);
        t.component("FormattedText");
        t.in_list("text", &|l| {
            let result = self.trace_lines_as_list(l);
            fit.set(Some(result));
        });
        t.bool("fits", matches!(fit.get(), Some(LayoutFit::Fitting { .. })));
    }
}

#[cfg(feature = "micropython")]
mod micropython {
    use crate::{error::Error, micropython::obj::Obj, ui::layout::obj::ComponentMsgObj};
    impl ComponentMsgObj for super::FormattedText {
        fn msg_try_into_obj(&self, _msg: Self::Msg) -> Result<Obj, Error> {
            unreachable!();
        }
    }
}

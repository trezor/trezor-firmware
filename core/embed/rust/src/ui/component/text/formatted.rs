use crate::ui::{
    component::{Component, Event, EventCtx, Never, Paginate},
    geometry::{Alignment, Offset, Rect},
    shape::Renderer,
};

use super::{
    layout::{LayoutFit, LayoutSink, TextNoOp, TextRenderer, TextRenderer2},
    op::OpTextLayout,
};

#[derive(Clone)]
pub struct FormattedText {
    op_layout: OpTextLayout<'static>,
    vertical: Alignment,
    char_offset: usize,
    y_offset: i16,
}

impl FormattedText {
    pub fn new(op_layout: OpTextLayout<'static>) -> Self {
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

    pub(crate) fn layout_content(&self, sink: &mut dyn LayoutSink) -> LayoutFit {
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
impl Paginate for FormattedText {
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

impl Component for FormattedText {
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

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.layout_content(&mut TextRenderer2::new(target));
    }
}

// DEBUG-ONLY SECTION BELOW

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for FormattedText {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        use crate::ui::component::text::layout::trace::TraceSink;
        use core::cell::Cell;
        let fit: Cell<Option<LayoutFit>> = Cell::new(None);
        t.component("FormattedText");
        t.in_list("text", &|l| {
            let result = self.layout_content(&mut TraceSink(l));
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

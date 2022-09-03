use crate::{
    micropython::{buffer::StrBuffer, util::ResultExt},
    ui::{
        component::Paginate,
        display::{Font, Icon, IconAndName},
        geometry::{Offset, Rect},
        model_tr::theme,
    },
};

use heapless::Vec;

use super::{
    flow_pages_poc_helpers::{
        LayoutFit, LayoutSink, LineAlignment, Op, TextLayout, TextNoOp, TextRenderer, TextStyle,
        ToDisplay,
    },
    ButtonActions, ButtonDetails, ButtonLayout,
};

/// Holding specific workflows that are created in `layout.rs`.
/// Is returning a `Page` (page/screen) on demand
/// based on the current page in `Flow`.
/// Before, when `layout.rs` was defining a `heapless::Vec` of `Page`s,
/// it was a very stack-expensive operation and StackOverflow was encountered.
/// With this "lazy-loading" approach (creating each page on demand) we can
/// have theoretically unlimited number of pages without triggering SO.
/// (Currently only the current page is stored on stack - in
/// `Flow::current_page`.)
pub struct FlowPages<F, const M: usize> {
    /// Function/closure that will return appropriate page on demand.
    get_page: F,
    /// Number of pages in the flow.
    page_count: u8,
}

impl<F, const M: usize> FlowPages<F, M>
where
    F: Fn(u8) -> Page<M>,
{
    pub fn new(get_page: F, page_count: u8) -> Self {
        Self {
            get_page,
            page_count,
        }
    }

    pub fn get(&self, page_index: u8) -> Page<M> {
        (self.get_page)(page_index)
    }

    pub fn count(&self) -> u8 {
        self.page_count
    }
}

#[derive(Clone)]
pub struct Page<const M: usize> {
    ops: Vec<Op, M>,
    layout: TextLayout,
    btn_layout: ButtonLayout<&'static str>,
    btn_actions: ButtonActions,
    current_page: usize,
    page_count: usize,
    char_offset: usize,
}

// For `layout.rs`
impl<const M: usize> Page<M> {
    pub fn new(btn_layout: ButtonLayout<&'static str>, btn_actions: ButtonActions) -> Self {
        let style = TextStyle::new(
            theme::FONT_NORMAL,
            theme::FG,
            theme::BG,
            theme::FG,
            theme::FG,
        );
        Self {
            ops: Vec::new(),
            layout: TextLayout::new(style),
            btn_layout,
            btn_actions,
            current_page: 0,
            page_count: 1,
            char_offset: 0,
        }
    }
}

// For `flow.rs`
impl<const M: usize> Page<M> {
    pub fn paint(&mut self) {
        self.change_page(self.current_page);
        self.layout_content(&mut TextRenderer);
    }

    pub fn btn_layout(&self) -> ButtonLayout<&'static str> {
        // When we are in pagination inside this flow,
        // show the up and down arrows on appropriate sides
        let current = self.btn_layout.clone();

        let btn_left = if self.has_prev_page() {
            Some(ButtonDetails::up_arrow_icon_wide())
        } else {
            current.btn_left
        };
        let btn_right = if self.has_next_page() {
            Some(ButtonDetails::down_arrow_icon_wide())
        } else {
            current.btn_right
        };

        ButtonLayout::new(btn_left, current.btn_middle, btn_right)
    }

    pub fn place(&mut self, bounds: Rect) -> Rect {
        self.layout.bounds = bounds;
        self.page_count = self.page_count();
        bounds
    }

    pub fn btn_actions(&self) -> ButtonActions {
        self.btn_actions.clone()
    }

    pub fn has_prev_page(&self) -> bool {
        self.current_page > 0
    }

    pub fn has_next_page(&self) -> bool {
        self.current_page < self.page_count - 1
    }

    pub fn go_to_prev_page(&mut self) {
        self.current_page -= 1;
    }

    pub fn go_to_next_page(&mut self) {
        self.current_page += 1;
    }
}

// For `layout.rs` - single operations
impl<const M: usize> Page<M> {
    pub fn with_new_item(mut self, item: Op) -> Self {
        self.ops
            .push(item)
            .assert_if_debugging_ui("Could not push to self.ops");
        self
    }

    pub fn text(self, text: StrBuffer) -> Self {
        self.with_new_item(Op::Text(ToDisplay::new(text)))
    }

    pub fn newline(self) -> Self {
        self.with_new_item(Op::Text(ToDisplay::new("\n".into())))
    }

    pub fn newline_half(self) -> Self {
        self.with_new_item(Op::Text(ToDisplay::new("\r".into())))
    }

    pub fn next_page(self) -> Self {
        self.with_new_item(Op::NextPage)
    }

    pub fn icon(self, icon: IconAndName) -> Self {
        self.with_new_item(Op::Icon(Icon::new(icon)))
    }

    pub fn font(self, font: Font) -> Self {
        self.with_new_item(Op::Font(font))
    }

    pub fn offset(self, offset: Offset) -> Self {
        self.with_new_item(Op::CursorOffset(offset))
    }

    pub fn alignment(self, alignment: LineAlignment) -> Self {
        self.with_new_item(Op::LineAlignment(alignment))
    }
}

// For `layout.rs` - aggregating operations
impl<const M: usize> Page<M> {
    pub fn icon_label_text(self, icon: IconAndName, label: StrBuffer, text: StrBuffer) -> Self {
        self.icon_with_offset(icon, 3)
            .text_normal(label)
            .newline()
            .text_bold(text)
    }

    pub fn icon_with_offset(self, icon: IconAndName, x_offset: i32) -> Self {
        self.icon(icon).offset(Offset::x(x_offset))
    }

    pub fn text_normal(self, text: StrBuffer) -> Self {
        self.font(theme::FONT_NORMAL).text(text)
    }

    pub fn text_bold(self, text: StrBuffer) -> Self {
        self.font(theme::FONT_BOLD).text(text)
    }
}

// For painting and pagination
impl<const M: usize> Page<M> {
    pub fn set_char_offset(&mut self, char_offset: usize) {
        self.char_offset = char_offset;
    }

    pub fn layout_content(&self, sink: &mut dyn LayoutSink) -> LayoutFit {
        let mut cursor = self.layout.initial_cursor();
        self.layout
            .layout_ops(self.ops.clone(), &mut cursor, self.char_offset, sink)
    }
}

// Pagination
impl<const M: usize> Paginate for Page<M> {
    fn page_count(&mut self) -> usize {
        let mut page_count = 1; // There's always at least one page.
        let mut char_offset = 0;

        // Make sure we're starting from the beginning.
        self.set_char_offset(char_offset);

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
                    self.set_char_offset(char_offset);
                }
            }
        }

        // Reset the char offset back to the beginning.
        self.set_char_offset(0);

        page_count
    }

    fn change_page(&mut self, to_page: usize) {
        let mut active_page = 0;
        let mut char_offset = 0;

        // Make sure we're starting from the beginning.
        self.set_char_offset(char_offset);

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
                    self.set_char_offset(char_offset);
                }
            }
        }
    }
}

#[cfg(feature = "ui_debug")]
pub mod trace {
    use crate::ui::model_tr::component::flow_pages_poc_helpers::TraceSink;

    use super::*;

    pub struct TraceText<'a, const M: usize>(pub &'a Page<M>);

    impl<'a, const M: usize> crate::trace::Trace for TraceText<'a, M> {
        fn trace(&self, d: &mut dyn crate::trace::Tracer) {
            d.content_flag();
            self.0.layout_content(&mut TraceSink(d));
            d.content_flag();
        }
    }
}

#[cfg(feature = "ui_debug")]
impl<const M: usize> crate::trace::Trace for Page<M> {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.open("Page");
        t.kw_pair("active_page", inttostr!(self.current_page as u8));
        t.kw_pair("page_count", inttostr!(self.page_count as u8));
        t.field("content", &trace::TraceText(self));
        t.close();
    }
}

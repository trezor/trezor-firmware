use crate::{
    micropython::{buffer::StrBuffer, util::ResultExt},
    ui::{
        component::Paginate,
        display::Font,
        geometry::{Offset, Rect},
        model_tr::theme,
    },
};

use heapless::Vec;

use super::{
    flow::BtnActions,
    flow_pages_poc_helpers::{
        LayoutFit, LayoutSink, LineAlignment, Op, TextLayout, TextNoOp, TextRenderer, TextStyle,
        ToDisplay,
    },
    ButtonDetails, ButtonLayout,
};

#[derive(Clone)]
pub struct FlowPageMaker<const M: usize> {
    ops: Vec<Op, M>,
    layout: TextLayout,
    btn_layout: ButtonLayout<&'static str>,
    btn_actions: BtnActions,
    current_page: usize,
    page_count: usize,
    char_offset: usize,
}

// For `layout.rs`
impl<const M: usize> FlowPageMaker<M> {
    pub fn new(btn_layout: ButtonLayout<&'static str>, btn_actions: BtnActions) -> Self {
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
impl<const M: usize> FlowPageMaker<M> {
    pub fn paint(&mut self) {
        self.change_page(self.current_page);
        self.layout_content(&mut TextRenderer);
    }

    pub fn btn_layout(&self) -> ButtonLayout<&'static str> {
        // When we are in pagination inside this flow,
        // show the up and down arrows on appropriate sides
        let current = self.btn_layout.clone();

        let btn_left = if self.has_prev_page() {
            Some(ButtonDetails::up_arrow_icon_wide("arr_up"))
        } else {
            current.btn_left
        };
        let btn_right = if self.has_next_page() {
            Some(ButtonDetails::down_arrow_icon_wide("arr_down"))
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

    pub fn btn_actions(&self) -> BtnActions {
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
impl<const M: usize> FlowPageMaker<M> {
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

    pub fn next_page(self) -> Self {
        self.with_new_item(Op::NextPage)
    }

    pub fn icon(self, icon: &'static [u8]) -> Self {
        self.with_new_item(Op::Icon(icon))
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
impl<const M: usize> FlowPageMaker<M> {
    pub fn icon_label_text(self, icon: &'static [u8], label: StrBuffer, text: StrBuffer) -> Self {
        self.icon_with_offset(icon, 3)
            .text_normal(label)
            .newline()
            .text_bold(text)
    }

    pub fn icon_with_offset(self, icon: &'static [u8], x_offset: i32) -> Self {
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
impl<const M: usize> FlowPageMaker<M> {
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
impl<const M: usize> Paginate for FlowPageMaker<M> {
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

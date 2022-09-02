use heapless::Vec;

use crate::ui::{
    component::{Component, Event, EventCtx, Never, Paginate},
    geometry::{Dimensions, Insets, LinearPlacement, Offset, Rect},
};

use super::{iter::LayoutFit, layout::TextStyle};

pub const MAX_PARAGRAPHS: usize = 6;
/// Maximum space between paragraphs. Actual result may be smaller (even 0) if
/// it would make paragraphs overflow the bounding box.
pub const DEFAULT_SPACING: i32 = 0;
/// Offset of paragraph text from the top of the paragraph bounding box. Tweak
/// these values to get nice alignment of baselines relative to the surrounding
/// components.
pub const PARAGRAPH_TOP_SPACE: i32 = -1;
/// Offset of paragraph bounding box bottom relative to bottom of its text.
pub const PARAGRAPH_BOTTOM_SPACE: i32 = 5;

pub const PARAGRAPH_INSETS: Insets = Insets::new(PARAGRAPH_TOP_SPACE, 0, PARAGRAPH_BOTTOM_SPACE, 0);

pub struct Paragraphs<T> {
    area: Rect,
    list: Vec<Paragraph<T>, MAX_PARAGRAPHS>,
    placement: LinearPlacement,
    offset: PageOffset,
    visible: usize,
}

impl<T> Paragraphs<T>
where
    T: AsRef<str>,
{
    pub fn new() -> Self {
        Self {
            area: Rect::zero(),
            list: Vec::new(),
            placement: LinearPlacement::vertical()
                .align_at_center()
                .with_spacing(DEFAULT_SPACING),
            offset: PageOffset::default(),
            visible: 0,
        }
    }

    pub fn with_placement(mut self, placement: LinearPlacement) -> Self {
        self.placement = placement;
        self
    }

    pub fn with_spacing(mut self, spacing: i32) -> Self {
        self.placement = self.placement.with_spacing(spacing);
        self
    }

    pub fn add(mut self, style: TextStyle, content: T) -> Self {
        if content.as_ref().is_empty() {
            return self;
        }
        let paragraph = Paragraph::new(content, style);
        if self.list.push(paragraph).is_err() {
            #[cfg(feature = "ui_debug")]
            panic!("paragraph list is full");
        }
        self
    }

    /// Update bounding boxes of paragraphs on the current page. First determine
    /// the number of visible paragraphs and their sizes. These are then
    /// arranged according to the layout.
    fn change_offset(&mut self, offset: PageOffset) {
        self.offset = offset;
        self.visible = 0;
        let mut char_offset = offset.chr;
        let mut remaining_area = self.area;

        for paragraph in &mut self.list[self.offset.par..] {
            let fit = paragraph.fit_text(remaining_area.size(), char_offset);
            if fit.lines == 0 {
                break;
            }
            let height = paragraph.style.text_font.lines_height(fit.lines);
            let (used, free) =
                remaining_area.split_top(height + PARAGRAPH_TOP_SPACE + PARAGRAPH_BOTTOM_SPACE);
            paragraph.fit(used);
            remaining_area = free;
            self.visible += 1;
            char_offset = 0;
        }

        self.placement.arrange(
            self.area,
            &mut self.list[offset.par..offset.par + self.visible],
        );
    }

    fn break_pages(&self) -> PageBreakIterator<T> {
        PageBreakIterator {
            paragraphs: self,
            current: None,
        }
    }
}

impl<T> Component for Paragraphs<T>
where
    T: AsRef<str>,
{
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.area = bounds;
        self.change_offset(self.offset);
        self.area
    }

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    fn paint(&mut self) {
        let mut char_offset = self.offset.chr;
        for paragraph in &self.list[self.offset.par..self.offset.par + self.visible] {
            paragraph.style.render_text(
                paragraph.content(char_offset),
                paragraph.bounds.inset(PARAGRAPH_INSETS),
            );
            char_offset = 0;
        }
    }

    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        sink(self.area);
        for paragraph in &self.list[self.offset.par..self.offset.par + self.visible] {
            sink(paragraph.bounds)
        }
    }
}

impl<T> Paginate for Paragraphs<T>
where
    T: AsRef<str>,
{
    fn page_count(&mut self) -> usize {
        // There's always at least one page.
        self.break_pages().count().max(1)
    }

    fn change_page(&mut self, to_page: usize) {
        if let Some(offset) = self.break_pages().nth(to_page) {
            self.change_offset(offset)
        } else {
            // Should not happen, set index past last paragraph to render empty page.
            self.offset = PageOffset {
                par: self.list.len(),
                chr: 0,
            };
            self.visible = 0;
        }
    }
}

pub struct Paragraph<T> {
    bounds: Rect,
    content: T,
    style: TextStyle,
}

impl<T> Paragraph<T>
where
    T: AsRef<str>,
{
    pub fn new(content: T, style: TextStyle) -> Self {
        Self {
            bounds: Rect::zero(),
            content,
            style,
        }
    }

    pub fn content(&self, char_offset: usize) -> &str {
        &self.content.as_ref()[char_offset..]
    }

    pub fn fit_text(&self, bounds: Offset, char_offset: usize) -> LayoutFit {
        let bounds_with_padding = Offset::new(
            bounds.x,
            bounds.y - PARAGRAPH_TOP_SPACE - PARAGRAPH_BOTTOM_SPACE,
        );
        self.style
            .fit_text(self.content(char_offset), bounds_with_padding, 0)
    }
}

impl<T> Dimensions for Paragraph<T>
where
    T: AsRef<str>,
{
    fn fit(&mut self, area: Rect) {
        self.bounds = area;
    }

    fn area(&self) -> Rect {
        self.bounds
    }
}

#[derive(Clone, Copy, Default, PartialEq, Eq)]
struct PageOffset {
    /// Index of paragraph.
    par: usize,

    /// Index of character in the paragraph.
    chr: usize,
}

struct PageBreakIterator<'a, T> {
    /// Reference to paragraph vector.
    paragraphs: &'a Paragraphs<T>,

    /// Current offset, or `None` before first `next()` call.
    current: Option<PageOffset>,
}

/// Yields indices to beginnings of successive pages. First value is always
/// `PageOffset { 0, 0 }` even if the paragraph vector is empty.
impl<'a, T> Iterator for PageBreakIterator<'a, T>
where
    T: AsRef<str>,
{
    /// `PageOffset` denotes the first paragraph that is rendered and a
    /// character offset in that paragraph.
    type Item = PageOffset;

    fn next(&mut self) -> Option<Self::Item> {
        let first = self.current.is_none();
        let current = self.current.get_or_insert_with(PageOffset::default);
        if first {
            return self.current;
        }

        let mut bounds = self.paragraphs.area.size();
        let mut progress = false;

        for paragraph in self.paragraphs.list.iter().skip(current.par) {
            let text = paragraph.content(current.chr);
            let fit = paragraph.fit_text(bounds, current.chr);
            if text.len() > fit.chars {
                // Text does not fit, assume whatever fits takes the entire remaining area.
                current.chr += fit.chars;
                if fit.chars == 0 && !progress {
                    // Nothing fits yet page is empty: terminate iterator to avoid looping
                    // forever.
                    return None;
                }
                // Return current offset.
                return self.current;
            } else {
                // Text fits, update remaining area.
                bounds =
                    bounds - Offset::y(fit.lines as i32 * paragraph.style.text_font.line_height());

                // Continue with start of next paragraph.
                current.par += 1;
                current.chr = 0;
                progress = true;
            }
        }

        // Last page.
        None
    }
}

#[cfg(feature = "ui_debug")]
pub mod trace {
    use crate::ui::component::text::iter::break_text_to_spans;

    use super::*;

    impl<T> crate::trace::Trace for Paragraphs<T>
    where
        T: AsRef<str>,
    {
        fn trace(&self, t: &mut dyn crate::trace::Tracer) {
            t.open("Paragraphs");
            let mut char_offset = self.offset.chr;
            for paragraph in self.list.iter().skip(self.offset.par).take(self.visible) {
                paragraph.trace(char_offset, t);
                t.string("\n");
                char_offset = 0;
            }
            t.close();
        }
    }

    impl<T> Paragraph<T>
    where
        T: AsRef<str>,
    {
        pub fn trace(&self, char_offset: usize, t: &mut dyn crate::trace::Tracer) {
            t.open("Paragraph");
            let max_lines = self.style.text_font.max_lines(self.bounds.height());
            for span in break_text_to_spans(
                self.content(char_offset),
                self.style.text_font,
                self.style.line_breaking,
                self.bounds.width(),
                0,
            )
            .take(max_lines as usize)
            {
                t.string(span.text);
                if span.end.is_linebreak() {
                    t.string("\n");
                }
            }
            t.close();
        }
    }
}

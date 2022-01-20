use heapless::Vec;

use crate::ui::{
    component::{Component, Event, EventCtx, Never, Paginate},
    display::Font,
    geometry::{Dimensions, LinearLayout, Offset, Rect},
};

use super::layout::{DefaultTextTheme, LayoutFit, TextLayout, TextNoOp, TextRenderer};

pub const MAX_PARAGRAPHS: usize = 6;
pub const DEFAULT_SPACING: i32 = 3;

pub struct Paragraphs<T> {
    area: Rect,
    list: Vec<Paragraph<T>, MAX_PARAGRAPHS>,
    layout: LinearLayout,
    offset: PageOffset,
    visible: usize,
}

impl<T> Paragraphs<T>
where
    T: AsRef<[u8]>,
{
    pub fn new(area: Rect) -> Self {
        Self {
            area,
            list: Vec::new(),
            layout: LinearLayout::vertical()
                .align_at_center()
                .with_spacing(DEFAULT_SPACING),
            offset: PageOffset::default(),
            visible: 0,
        }
    }

    pub fn with_layout(mut self, layout: LinearLayout) -> Self {
        self.layout = layout;
        self
    }

    pub fn with_spacing(mut self, spacing: i32) -> Self {
        self.layout = self.layout.with_spacing(spacing);
        self
    }

    pub fn add<D: DefaultTextTheme>(mut self, text_font: Font, content: T) -> Self {
        if content.as_ref().is_empty() {
            return self;
        }
        let paragraph = Paragraph::new(
            content,
            TextLayout {
                text_font,
                ..TextLayout::new::<D>(self.area)
            },
        );
        if self.list.push(paragraph).is_err() {
            #[cfg(feature = "ui_debug")]
            panic!("paragraph list is full");
        }
        self
    }

    /// Update bounding boxes of paragraphs on the current page.
    fn arrange_visible(&mut self) {
        let mut char_offset = self.offset.chr;
        let mut remaining_area = self.area;

        for paragraph in self
            .list
            .iter_mut()
            .skip(self.offset.par)
            .take(self.visible)
        {
            paragraph.set_area(remaining_area);
            let height = paragraph
                .layout
                .measure_text_height(&paragraph.content.as_ref()[char_offset..]);
            let (used, free) = remaining_area.split_top(height);
            paragraph.set_area(used);
            remaining_area = free;
            char_offset = 0;
        }

        let visible = &mut self.list[self.offset.par..self.offset.par + self.visible];
        self.layout.arrange(self.area, visible);
    }

    fn break_pages<'a>(&'a self) -> PageBreakIterator<'a, T> {
        PageBreakIterator {
            paragraphs: self,
            upcoming: PageOffset::default(),
        }
    }
}

impl<T> Component for Paragraphs<T>
where
    T: AsRef<[u8]>,
{
    type Msg = Never;

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    fn paint(&mut self) {
        let mut char_offset = self.offset.chr;
        for paragraph in self.list.iter().skip(self.offset.par).take(self.visible) {
            paragraph.layout.layout_text(
                &paragraph.content.as_ref()[char_offset..],
                &mut paragraph.layout.initial_cursor(),
                &mut TextRenderer,
            );
            char_offset = 0;
        }
    }
}

impl<T> Dimensions for Paragraphs<T> {
    fn get_size(&mut self) -> Offset {
        self.area.size()
    }

    fn set_area(&mut self, area: Rect) {
        self.area = area
    }
}

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for Paragraphs<T>
where
    T: AsRef<[u8]>,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.open("Paragraphs");
        for paragraph in &self.list {
            paragraph.trace(t);
        }
        t.close();
    }

    fn bounds(&self, sink: &dyn Fn(Rect)) {
        sink(self.area);
        for paragraph in self.list.iter().skip(self.offset.par).take(self.visible) {
            paragraph.bounds(sink);
        }
    }
}

pub struct Paragraph<T> {
    content: T,
    layout: TextLayout,
}

impl<T> Paragraph<T>
where
    T: AsRef<[u8]>,
{
    pub fn new(content: T, layout: TextLayout) -> Self {
        Self { content, layout }
    }
}

impl<T> Dimensions for Paragraph<T>
where
    T: AsRef<[u8]>,
{
    fn get_size(&mut self) -> Offset {
        self.layout.bounds.size()
    }

    fn set_area(&mut self, area: Rect) {
        self.layout.bounds = area;
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

    /// Next offset returned by the iterator. Internally the iterator is one
    /// page ahead because it needs to find the end of the page to determine
    /// number of visible paragraphs.
    upcoming: PageOffset,
}

/// Yields indices to beginnings of successive pages, plus number of visible
/// paragraphs on each page. First value is always `PageOffset { 0, 0 }` for
/// non-empty iterator.
impl<'a, T> Iterator for PageBreakIterator<'a, T>
where
    T: AsRef<[u8]>,
{
    /// `PageOffset` denotes the first paragraph that is rendered and a
    /// character offset in that paragraph. The second value of the tuple is
    /// the number of paragraphs displayed on a page.
    type Item = (PageOffset, usize);

    fn next(&mut self) -> Option<Self::Item> {
        if self.upcoming.par >= self.paragraphs.list.len() {
            return None;
        }

        let result = self.upcoming;
        let mut remaining_area = self.paragraphs.area;
        let mut visible = 0;

        for paragraph in self.paragraphs.list.iter().skip(self.upcoming.par) {
            loop {
                let mut temp_layout = paragraph.layout;
                temp_layout.bounds = remaining_area;

                let fit = temp_layout.layout_text(
                    &paragraph.content.as_ref()[self.upcoming.chr..],
                    &mut temp_layout.initial_cursor(),
                    &mut TextNoOp,
                );
                match fit {
                    LayoutFit::Fitting { size, .. } => {
                        // Text fits, update remaining area.
                        remaining_area = remaining_area.split_top(size.y).1;

                        // Continue with start of next paragraph.
                        self.upcoming.par += 1;
                        self.upcoming.chr = 0;
                        visible += 1;
                        break;
                    }
                    LayoutFit::OutOfBounds { processed_chars } => {
                        // Text does not fit, assume whatever fits takes the entire remaining area.
                        self.upcoming.chr += processed_chars;
                        if processed_chars > 0 {
                            visible += 1
                        } else if self.upcoming == result {
                            // Nothing fits yet page is empty: terminate iterator to avoid looping
                            // forever.
                            return None;
                        }
                        // Return pointer to start of page.
                        return Some((result, visible));
                    }
                }
            }
        }

        // Last page.
        Some((result, visible))
    }
}

impl<T> Paginate for Paragraphs<T>
where
    T: AsRef<[u8]>,
{
    fn page_count(&mut self) -> usize {
        // There's always at least one page.
        self.break_pages().count().max(1)
    }

    fn change_page(&mut self, to_page: usize) {
        if let Some((offset, visible)) = self.break_pages().skip(to_page).next() {
            // Set span of currently visible paragraphs.
            self.offset = offset;
            self.visible = visible;

            // Arrange visible paragraphs.
            self.arrange_visible()
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

#[cfg(feature = "ui_debug")]
pub mod trace {
    use crate::ui::component::text::layout::trace::TraceSink;

    use super::*;

    pub struct TraceText<'a, T>(pub &'a Paragraph<T>);

    impl<'a, T> crate::trace::Trace for TraceText<'a, T>
    where
        T: AsRef<[u8]>,
    {
        fn trace(&self, d: &mut dyn crate::trace::Tracer) {
            self.0.layout.layout_text(
                self.0.content.as_ref(),
                &mut self.0.layout.initial_cursor(),
                &mut TraceSink(d),
            );
        }
    }
}

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for Paragraph<T>
where
    T: AsRef<[u8]>,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.open("Paragraph");
        t.field("content", &trace::TraceText(self));
        t.close();
    }

    fn bounds(&self, sink: &dyn Fn(Rect)) {
        sink(self.layout.bounds);
    }
}

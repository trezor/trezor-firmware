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
    para_offset: usize,
    char_offset: usize,
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
            para_offset: 0,
            char_offset: 0,
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

    fn break_pages<'a>(&'a mut self) -> PageBreakIterator<'a, T> {
        PageBreakIterator {
            paragraphs: self,
            para_offset: 0,
            char_offset: 0,
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
        let mut char_offset = self.char_offset;
        for paragraph in self.list.iter().skip(self.para_offset) {
            let fit = paragraph.layout.layout_text(
                &paragraph.content.as_ref()[char_offset..],
                &mut paragraph.layout.initial_cursor(),
                &mut TextRenderer,
            );
            if matches!(fit, LayoutFit::OutOfBounds { .. }) {
                break;
            }
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

struct PageBreakIterator<'a, T> {
    paragraphs: &'a mut Paragraphs<T>,
    para_offset: usize,
    char_offset: usize,
}

/// Yields indices to beginnings of successive pages. As a side effect it
/// updates the bounding box of each paragraph on the page. Because a paragraph
/// can be rendered on multiple pages, such bounding boxes are only valid for
/// paragraphs processed in the last call to `next`.
///
/// The boxes are simply stacked below each other and may be further arranged
/// before drawing.
impl<'a, T> Iterator for PageBreakIterator<'a, T>
where
    T: AsRef<[u8]>,
{
    /// Paragraph index, character index, number of paragraphs shown.
    type Item = (usize, usize, usize);

    fn next(&mut self) -> Option<Self::Item> {
        if self.para_offset >= self.paragraphs.list.len() {
            return None;
        }

        let old_para_offset = self.para_offset;
        let old_char_offset = self.char_offset;
        let mut area = self.paragraphs.area;

        for paragraph in self.paragraphs.list.iter_mut().skip(self.para_offset) {
            loop {
                paragraph.set_area(area);
                let fit = paragraph.layout.layout_text(
                    &paragraph.content.as_ref()[self.char_offset..],
                    &mut paragraph.layout.initial_cursor(),
                    &mut TextNoOp,
                );
                match fit {
                    LayoutFit::Fitting { size, .. } => {
                        // Text fits, update the bounding box.
                        let (used, free) = area.split_top(size.y);
                        paragraph.set_area(used);
                        // Continue with next paragraph in remaining space.
                        area = free;
                        self.char_offset = 0;
                        self.para_offset += 1;
                        break;
                    }
                    LayoutFit::OutOfBounds { processed_chars } => {
                        // Text does not fit, assume whatever fits takes the entire remaining area.
                        self.char_offset += processed_chars;
                        let visible = if processed_chars > 0 {
                            self.para_offset - old_para_offset + 1
                        } else {
                            self.para_offset - old_para_offset
                        };
                        // Return pointer to start of page.
                        return Some((old_para_offset, old_char_offset, visible));
                    }
                }
            }
        }

        // Last page.
        Some((
            old_para_offset,
            old_char_offset,
            self.para_offset - old_para_offset,
        ))
    }
}

impl<T> Paginate for Paragraphs<T>
where
    T: AsRef<[u8]>,
{
    fn page_count(&mut self) -> usize {
        // There's always at least one page.
        let page_count = self.break_pages().count().max(1);

        // Reset to first page.
        self.change_page(0);

        page_count
    }

    fn change_page(&mut self, to_page: usize) {
        if let Some((para_offset, char_offset, para_visible)) =
            self.break_pages().skip(to_page).next()
        {
            // Set offsets used by `paint`.
            self.para_offset = para_offset;
            self.char_offset = char_offset;

            // Arrange visible paragraphs.
            let visible = &mut self.list[para_offset..para_offset + para_visible];
            self.layout.arrange(self.area, visible);
        } else {
            // Should not happen, set index past last paragraph to render empty page.
            self.para_offset = self.list.len();
            self.char_offset = 0;
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
}

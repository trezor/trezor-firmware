use heapless::Vec;

use crate::ui::{
    component::{Component, Event, EventCtx, Never, Paginate},
    display::{self, Color},
    geometry::{Alignment, Dimensions, Insets, LinearPlacement, Offset, Point, Rect},
};

use super::layout::{LayoutFit, TextLayout, TextStyle};

pub const MAX_PARAGRAPHS: usize = 9;
/// Maximum space between paragraphs. Actual result may be smaller (even 0) if
/// it would make paragraphs overflow the bounding box.
pub const DEFAULT_SPACING: i32 = 0;
/// Offset of paragraph text from the top of the paragraph bounding box. Tweak
/// these values to get nice alignment of baselines relative to the surrounding
/// components.
pub const PARAGRAPH_TOP_SPACE: i32 = -1;
/// Offset of paragraph bounding box bottom relative to bottom of its text.
pub const PARAGRAPH_BOTTOM_SPACE: i32 = 5;

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

    pub fn add_color(self, style: TextStyle, color: Color, content: T) -> Self {
        let color_style = TextStyle {
            text_color: color,
            ..style
        };
        self.add(color_style, content)
    }

    pub fn add(mut self, style: TextStyle, content: T) -> Self {
        if content.as_ref().is_empty() {
            return self;
        }
        let paragraph = Paragraph::new(
            content,
            TextLayout {
                padding_top: PARAGRAPH_TOP_SPACE,
                padding_bottom: PARAGRAPH_BOTTOM_SPACE,
                ..TextLayout::new(style)
            },
        );
        if self.list.push(paragraph).is_err() {
            #[cfg(feature = "ui_debug")]
            panic!("paragraph list is full");
        }
        self
    }

    pub fn centered(mut self) -> Self {
        if let Some(ref mut para) = self.list.last_mut() {
            para.layout.align = Alignment::Center;
        };
        self
    }

    pub fn add_break(mut self) -> Self {
        if let Some(ref mut para) = self.list.last_mut() {
            para.break_after = true;
        };
        self
    }

    pub fn update(&mut self, i: usize, content: T) {
        if i < self.list.len() {
            self.list[i].content = content;
            self.change_offset(PageOffset::default());
        }
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
            paragraph.fit(remaining_area);
            let height = paragraph
                .layout
                .fit_text(paragraph.content(char_offset))
                .height();
            if height == 0 {
                break;
            }
            let (used, free) = remaining_area.split_top(height);
            paragraph.fit(used);
            remaining_area = free;
            self.visible += 1;
            char_offset = 0;

            if paragraph.break_after {
                break;
            }
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
            paragraph.layout.render_text(paragraph.content(char_offset));
            char_offset = 0;
        }
    }

    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        sink(self.area);
        for paragraph in &self.list[self.offset.par..self.offset.par + self.visible] {
            sink(paragraph.layout.bounds)
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

#[cfg(feature = "ui_debug")]
pub mod trace {
    use crate::ui::component::text::layout::trace::TraceSink;

    use super::*;

    impl<T> crate::trace::Trace for Paragraphs<T>
    where
        T: AsRef<str>,
    {
        fn trace(&self, t: &mut dyn crate::trace::Tracer) {
            t.open("Paragraphs");
            let mut char_offset = self.offset.chr;
            for paragraph in self.list.iter().skip(self.offset.par).take(self.visible) {
                paragraph.layout.layout_text(
                    paragraph.content(char_offset),
                    &mut paragraph.layout.initial_cursor(),
                    &mut TraceSink(t),
                );
                t.string("\n");
                char_offset = 0;
            }
            t.close();
        }
    }
}

pub struct Paragraph<T> {
    content: T,
    layout: TextLayout,
    break_after: bool,
}

impl<T> Paragraph<T>
where
    T: AsRef<str>,
{
    pub fn new(content: T, layout: TextLayout) -> Self {
        Self {
            content,
            layout,
            break_after: false,
        }
    }

    pub fn content(&self, char_offset: usize) -> &str {
        &self.content.as_ref()[char_offset..]
    }
}

impl<T> Dimensions for Paragraph<T>
where
    T: AsRef<str>,
{
    fn fit(&mut self, area: Rect) {
        self.layout.bounds = area;
    }

    fn area(&self) -> Rect {
        self.layout.bounds
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

        let mut remaining_area = self.paragraphs.area;
        let mut progress = false;

        for paragraph in self.paragraphs.list.iter().skip(current.par) {
            let fit = paragraph
                .layout
                .with_bounds(remaining_area)
                .fit_text(paragraph.content(current.chr));
            match fit {
                LayoutFit::Fitting { height, .. } => {
                    // Text fits, update remaining area.
                    remaining_area = remaining_area.inset(Insets::top(height));

                    // Continue with start of next paragraph.
                    current.par += 1;
                    current.chr = 0;
                    progress = true;

                    // Handle hard break if requested for this paragraph.
                    if paragraph.break_after && current.par < self.paragraphs.list.len() {
                        return self.current;
                    }
                }
                LayoutFit::OutOfBounds {
                    processed_chars, ..
                } => {
                    // Text does not fit, assume whatever fits takes the entire remaining area.
                    current.chr += processed_chars;
                    if processed_chars == 0 && !progress {
                        // Nothing fits yet page is empty: terminate iterator to avoid looping
                        // forever.
                        return None;
                    }
                    // Return current offset.
                    return self.current;
                }
            }
        }

        // Last page.
        None
    }
}

pub struct Checklist<T> {
    area: Rect,
    paragraphs: Paragraphs<T>,
    current: usize,
    icon_current: &'static [u8],
    icon_done: &'static [u8],
}

impl<T> Checklist<T>
where
    T: AsRef<str>,
{
    const CHECK_WIDTH: i32 = 16;
    const DONE_OFFSET: Offset = Offset::new(-2, 6);
    const CURRENT_OFFSET: Offset = Offset::new(2, 3);

    pub fn from_paragraphs(
        icon_current: &'static [u8],
        icon_done: &'static [u8],
        current: usize,
        paragraphs: Paragraphs<T>,
    ) -> Self {
        Self {
            area: Rect::zero(),
            paragraphs,
            current,
            icon_current,
            icon_done,
        }
    }

    fn paint_icon(&self, index: usize, icon: &'static [u8], offset: Offset) {
        let para = self.paragraphs.list[index].layout;
        let top_left = Point::new(self.area.x0, para.bounds.y0);
        display::icon_top_left(
            top_left + offset,
            icon,
            para.style.text_color,
            para.style.background_color,
        );
    }
}

impl<T> Component for Checklist<T>
where
    T: AsRef<str>,
{
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.area = bounds;
        let para_area = bounds.inset(Insets::left(Self::CHECK_WIDTH));
        self.paragraphs.place(para_area);
        self.area
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.paragraphs.event(ctx, event)
    }

    fn paint(&mut self) {
        self.paragraphs.paint();
        let first = self.paragraphs.offset.par;
        let last = first + self.paragraphs.visible;
        for i in first..last.min(self.current) {
            self.paint_icon(i, self.icon_done, Self::DONE_OFFSET);
        }
        self.paint_icon(self.current, self.icon_current, Self::CURRENT_OFFSET)
    }

    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        sink(self.area);
        self.paragraphs.bounds(sink);
    }
}

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for Checklist<T>
where
    T: AsRef<str>,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.open("Checklist");
        t.field("current", &self.current);
        t.field("items", &self.paragraphs);
        t.close();
    }
}

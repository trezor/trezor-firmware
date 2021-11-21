use heapless::Vec;

use crate::ui::{
    component::{Component, Event, EventCtx, Never},
    display::Font,
    geometry::{Dimensions, LinearLayout, Offset, Rect},
};

use super::layout::{TextLayout, TextNoop, TextRenderer};

pub const MAX_PARAGRAPHS: usize = 6;

pub struct Paragraphs<T> {
    area: Rect,
    list: Vec<Paragraph<T>, MAX_PARAGRAPHS>,
    layout: LinearLayout,
}

impl<T> Paragraphs<T>
where
    T: AsRef<[u8]>,
{
    pub fn new(area: Rect) -> Self {
        Self {
            area,
            list: Vec::new(),
            layout: LinearLayout::vertical().align_at_center().with_spacing(10),
        }
    }

    pub fn with_layout(mut self, layout: LinearLayout) -> Self {
        self.layout = layout;
        self
    }

    pub fn add(mut self, text_font: Font, content: T) -> Self {
        let paragraph = Paragraph::new(
            content,
            TextLayout {
                text_font,
                ..TextLayout::new(self.area)
            },
        );
        if self.list.push(paragraph).is_err() {
            #[cfg(feature = "ui_debug")]
            panic!("paragraph list is full");
        }
        self
    }

    pub fn arrange(mut self) -> Self {
        self.layout.arrange(self.area, &mut self.list);
        self
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
        for paragraph in &mut self.list {
            paragraph.paint();
        }
    }
}

pub struct Paragraph<T> {
    content: T,
    layout: TextLayout,
    size: Offset,
}

impl<T> Paragraph<T>
where
    T: AsRef<[u8]>,
{
    pub fn new(content: T, layout: TextLayout) -> Self {
        Self {
            size: Self::measure(&content, layout),
            content,
            layout,
        }
    }

    fn measure(content: &T, layout: TextLayout) -> Offset {
        let mut cursor = layout.initial_cursor();
        layout.layout_text(content.as_ref(), &mut cursor, &mut TextNoop);
        let width = layout.bounds.width();
        let height = cursor.y - layout.initial_cursor().y;
        Offset::new(width, height)
    }
}

impl<T> Dimensions for Paragraph<T>
where
    T: AsRef<[u8]>,
{
    fn get_size(&mut self) -> Offset {
        self.size
    }

    fn set_area(&mut self, area: Rect) {
        self.layout.bounds = area;
    }
}

impl<T> Component for Paragraph<T>
where
    T: AsRef<[u8]>,
{
    type Msg = Never;

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    fn paint(&mut self) {
        self.layout.layout_text(
            self.content.as_ref(),
            &mut self.layout.initial_cursor(),
            &mut TextRenderer,
        );
    }
}

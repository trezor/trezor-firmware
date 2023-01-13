use crate::ui::{
    component::{Component, Event, EventCtx, Never},
    display::Font,
    geometry::{Alignment, Offset, Rect},
};

use super::{text::TextStyle, TextLayout};

pub struct Label<T> {
    text: T,
    layout: TextLayout,
}

impl<T> Label<T>
where
    T: AsRef<str>,
{
    pub fn new(text: T, align: Alignment, style: TextStyle) -> Self {
        Self {
            text,
            layout: TextLayout::new(style).with_align(align),
        }
    }

    pub fn left_aligned(text: T, style: TextStyle) -> Self {
        Self::new(text, Alignment::Start, style)
    }

    pub fn right_aligned(text: T, style: TextStyle) -> Self {
        Self::new(text, Alignment::End, style)
    }

    pub fn centered(text: T, style: TextStyle) -> Self {
        Self::new(text, Alignment::Center, style)
    }

    pub fn text(&self) -> &T {
        &self.text
    }

    pub fn set_text(&mut self, text: T) {
        self.text = text;
    }

    pub fn font(&self) -> Font {
        self.layout.style.text_font
    }

    pub fn area(&self) -> Rect {
        self.layout.bounds
    }

    pub fn max_size(&self) -> Offset {
        let font = self.font();
        Offset::new(font.text_width(self.text.as_ref()), font.text_max_height())
    }
}

impl<T> Component for Label<T>
where
    T: AsRef<str>,
{
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        let height = self
            .layout
            .with_bounds(bounds)
            .fit_text(self.text.as_ref())
            .height();
        self.layout = self.layout.with_bounds(bounds.with_height(height));
        self.layout.bounds
    }

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    fn paint(&mut self) {
        self.layout.render_text(self.text.as_ref());
    }

    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        sink(self.layout.bounds)
    }
}

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for Label<T>
where
    T: AsRef<str>,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.string(self.text.as_ref())
    }
}

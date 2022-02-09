use core::ops::Deref;

use crate::ui::{
    component::{Component, Event, EventCtx, Never},
    display::{self, Color, Font},
    geometry::{Alignment, Offset, Rect},
};

pub struct LabelStyle {
    pub font: Font,
    pub text_color: Color,
    pub background_color: Color,
}

pub struct Label<T> {
    area: Rect,
    align: Alignment,
    style: LabelStyle,
    text: T,
}

impl<T> Label<T>
where
    T: Deref<Target = str>,
{
    pub fn new(text: T, align: Alignment, style: LabelStyle) -> Self {
        Self {
            area: Rect::zero(),
            align,
            style,
            text,
        }
    }

    pub fn left_aligned(text: T, style: LabelStyle) -> Self {
        Self::new(text, Alignment::Start, style)
    }

    pub fn right_aligned(text: T, style: LabelStyle) -> Self {
        Self::new(text, Alignment::End, style)
    }

    pub fn centered(text: T, style: LabelStyle) -> Self {
        Self::new(text, Alignment::Center, style)
    }

    pub fn text(&self) -> &T {
        &self.text
    }

    pub fn size(&self) -> Offset {
        Offset::new(
            self.style.font.text_width(&self.text),
            self.style.font.text_height(),
        )
    }
}

impl<T> Component for Label<T>
where
    T: Deref<Target = str>,
{
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        let origin = match self.align {
            Alignment::Start => bounds.top_left(),
            Alignment::Center => bounds.top_left().center(bounds.top_right()),
            Alignment::End => bounds.top_right(),
        };
        let size = self.size();
        let top_left = size.snap(origin, self.align, Alignment::Start);
        self.area = Rect::from_top_left_and_size(top_left, size);
        self.area
    }

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    fn paint(&mut self) {
        display::text(
            self.area.bottom_left(),
            &self.text,
            self.style.font,
            self.style.text_color,
            self.style.background_color,
        );
    }

    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        sink(self.area)
    }
}

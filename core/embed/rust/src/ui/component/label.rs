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
    T: Deref<Target = [u8]>,
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
}

impl<T> Component for Label<T>
where
    T: Deref<Target = [u8]>,
{
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        let size = Offset::new(
            self.style.font.text_width(&self.text),
            self.style.font.line_height(),
        );
        self.area = match self.align {
            Alignment::Start => Rect::from_top_left_and_size(bounds.top_left(), size),
            Alignment::Center => {
                let origin = bounds.top_left().center(bounds.top_right());
                Rect {
                    x0: origin.x - size.x / 2,
                    y0: origin.y,
                    x1: origin.x + size.x / 2,
                    y1: origin.y + size.y,
                }
            }
            Alignment::End => {
                let origin = bounds.top_right();
                Rect {
                    x0: origin.x - size.x,
                    y0: origin.y,
                    x1: origin.x,
                    y1: origin.y + size.y,
                }
            }
        };
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
}

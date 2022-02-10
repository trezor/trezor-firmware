use core::ops::Deref;

use crate::ui::{
    component::{Component, Event, EventCtx, Never},
    display::{self, Color, Font},
    geometry::{Alignment, Point, Rect},
};

pub struct LabelStyle {
    pub font: Font,
    pub text_color: Color,
    pub background_color: Color,
}

pub struct Label<T> {
    area: Rect,
    style: LabelStyle,
    text: T,
}

impl<T> Label<T>
where
    T: Deref<Target = [u8]>,
{
    pub fn new(origin: Point, align: Alignment, text: T, style: LabelStyle) -> Self {
        let width = display::text_width(&text, style.font);
        let height = style.font.line_height();
        let area = match align {
            // `origin` is the top-left point.
            Alignment::Start => Rect {
                x0: origin.x,
                y0: origin.y,
                x1: origin.x + width,
                y1: origin.y + height,
            },
            // `origin` is the top-centered point.
            Alignment::Center => Rect {
                x0: origin.x - width / 2,
                y0: origin.y,
                x1: origin.x + width / 2,
                y1: origin.y + height,
            },
            // `origin` is the top-right point.
            Alignment::End => Rect {
                x0: origin.x - width,
                y0: origin.y,
                x1: origin.x,
                y1: origin.y + height,
            },
        };
        Self { area, style, text }
    }

    pub fn left_aligned(origin: Point, text: T, style: LabelStyle) -> Self {
        Self::new(origin, Alignment::Start, text, style)
    }

    pub fn right_aligned(origin: Point, text: T, style: LabelStyle) -> Self {
        Self::new(origin, Alignment::End, text, style)
    }

    pub fn centered(origin: Point, text: T, style: LabelStyle) -> Self {
        Self::new(origin, Alignment::Center, text, style)
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

use core::ops::Deref;

use crate::ui::{
    display,
    math::{Align, Color, Point, Rect},
};

use super::component::{Component, Event, EventCtx, Widget};

pub struct Label<T> {
    widget: Widget,
    style: LabelStyle,
    text: T,
}

impl<T: Deref<Target = [u8]>> Label<T> {
    pub fn new(origin: Point, align: Align, text: T, style: LabelStyle) -> Self {
        let width = display::text_width(&text, style.font);
        let height = display::line_height();
        let area = match align {
            // `origin` is the top-left point.
            Align::Left => Rect {
                x0: origin.x,
                y0: origin.y,
                x1: origin.x + width,
                y1: origin.y + height,
            },
            // `origin` is the top-right point.
            Align::Right => Rect {
                x0: origin.x - width,
                y0: origin.y,
                x1: origin.x,
                y1: origin.y + height,
            },
            // `origin` is the top-centered point.
            Align::Center => Rect {
                x0: origin.x - width / 2,
                y0: origin.y,
                x1: origin.x + width / 2,
                y1: origin.y + height,
            },
        };
        Self {
            widget: Widget::new(area),
            text,
            style,
        }
    }

    pub fn left_aligned(origin: Point, text: T, style: LabelStyle) -> Self {
        Self::new(origin, Align::Left, text, style)
    }

    pub fn right_aligned(origin: Point, text: T, style: LabelStyle) -> Self {
        Self::new(origin, Align::Right, text, style)
    }

    pub fn centered(origin: Point, text: T, style: LabelStyle) -> Self {
        Self::new(origin, Align::Center, text, style)
    }

    pub fn text(&self) -> &T {
        &self.text
    }
}

pub struct LabelStyle {
    pub font: i32,
    pub text_color: Color,
    pub background_color: Color,
}

impl<T: Deref<Target = [u8]>> Component for Label<T> {
    type Msg = !;

    fn widget(&mut self) -> &mut Widget {
        &mut self.widget
    }

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    fn paint(&mut self) {
        display::text(
            self.area().bottom_left(),
            &self.text,
            self.style.font,
            self.style.text_color,
            self.style.background_color,
        );
    }
}

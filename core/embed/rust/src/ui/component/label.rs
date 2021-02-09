use core::ops::Deref;

use crate::ui::display;
use crate::ui::math::{Align, Point, Rect};

use super::component::{Component, Widget};

pub struct Label<T> {
    widget: Widget,
    style: LabelStyle,
    text: T,
}

impl<T: Deref<Target = [u8]>> Label<T> {
    pub fn new(text: T, style: LabelStyle, origin: Point, align: Align) -> Self {
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

    pub fn left_aligned(text: T, style: LabelStyle, origin: Point) -> Self {
        Self::new(text, style, origin, Align::Left)
    }

    pub fn right_aligned(text: T, style: LabelStyle, origin: Point) -> Self {
        Self::new(text, style, origin, Align::Right)
    }

    pub fn centered(text: T, style: LabelStyle, origin: Point) -> Self {
        Self::new(text, style, origin, Align::Center)
    }

    pub fn text(&self) -> &T {
        &self.text
    }
}

pub struct LabelStyle {
    pub font: i32,
    pub text_color: u16,
    pub background_color: u16,
}

impl<T: Deref<Target = [u8]>> Component for Label<T> {
    type Msg = ();

    fn widget(&mut self) -> &mut Widget {
        &mut self.widget
    }

    fn paint(&mut self) {
        display::text(
            self.area().top_left(),
            &self.text,
            self.style.font,
            self.style.text_color,
            self.style.background_color,
        );
    }
}

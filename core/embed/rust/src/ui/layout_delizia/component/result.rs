use super::super::fonts;
use super::constant::WIDTH;
use super::theme::{FG, RESULT_FOOTER_START, RESULT_PADDING};
use crate::ui::component::text::TextStyle;
use crate::ui::component::{Component, Event, EventCtx, Label, Never};
use crate::ui::constant::screen;
use crate::ui::display::Color;
use crate::ui::geometry::{Offset, Point, Rect};
use crate::ui::shape::{self, Renderer};

pub struct ResultStyle {
    pub fg_color: Color,
    pub bg_color: Color,
    pub divider_color: Color,
}

impl ResultStyle {
    pub const fn new(fg_color: Color, bg_color: Color, divider_color: Color) -> Self {
        Self {
            fg_color,
            bg_color,
            divider_color,
        }
    }

    pub const fn message_style(&self) -> TextStyle {
        TextStyle::new(fonts::FONT_DEMIBOLD, self.fg_color, self.bg_color, FG, FG)
    }

    pub const fn title_style(&self) -> TextStyle {
        TextStyle::new(fonts::FONT_DEMIBOLD, self.fg_color, self.bg_color, FG, FG)
    }
}

pub struct ResultFooter<'a> {
    style: &'a ResultStyle,
    text: Label<'a>,
    area: Rect,
}

impl<'a> ResultFooter<'a> {
    pub fn new(text: Label<'a>, style: &'a ResultStyle) -> Self {
        Self {
            style,
            text,
            area: Rect::zero(),
        }
    }
}

impl ResultFooter<'_> {
    pub const fn split_bounds() -> (Rect, Rect) {
        let main_area = Rect::new(
            Point::new(RESULT_PADDING, 0),
            Point::new(WIDTH - RESULT_PADDING, RESULT_FOOTER_START),
        );
        let footer_area = Rect::new(
            Point::new(RESULT_PADDING, RESULT_FOOTER_START),
            Point::new(WIDTH - RESULT_PADDING, screen().height()),
        );
        (main_area, footer_area)
    }
}

impl Component for ResultFooter<'_> {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.area = bounds;
        self.text.place(bounds);
        bounds
    }

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        // divider line
        let bar = Rect::from_center_and_size(
            Point::new(self.area.center().x, self.area.y0),
            Offset::new(self.area.width(), 1),
        );
        shape::Bar::new(bar)
            .with_fg(self.style.divider_color)
            .render(target);

        // footer text
        self.text.render(target);
    }
}

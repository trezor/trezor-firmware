use crate::ui::{
    component::{Component, Event, EventCtx, Never, Pad},
    display::Font,
    geometry::{Point, Rect},
};

use super::{common, flow_pages_poc_helpers::LineAlignment, theme};

/// Component that allows for "allocating" a standalone line of text anywhere
/// on the screen and updating it arbitrarily - without affecting the rest
/// and without being affected by other components.
pub struct ChangingTextLine<T> {
    area: Rect,
    pad: Pad,
    text: T,
    font: Font,
    line_alignment: LineAlignment,
}

impl<T> ChangingTextLine<T>
where
    T: AsRef<str>,
{
    pub fn new(text: T, font: Font, line_alignment: LineAlignment) -> Self {
        Self {
            area: Rect::zero(),
            pad: Pad::with_background(theme::BG),
            text,
            font,
            line_alignment,
        }
    }

    pub fn center_mono(text: T) -> Self {
        Self::new(text, Font::MONO, LineAlignment::Center)
    }

    pub fn update_text(&mut self, text: T) {
        self.text = text;
        self.pad.clear();
    }

    /// Gets the height that is needed for this line to fit perfectly
    /// without affecting the rest of the screen.
    /// (Accounting for letters that go below the baseline (y, j, ...).)
    pub fn needed_height(&self) -> i16 {
        self.font.line_height() + 2
    }

    /// Y coordinate of text baseline, is the same for all paints.
    fn y_baseline(&self) -> i16 {
        self.area.y0 + self.font.line_height()
    }

    fn paint_left(&self) {
        let baseline = Point::new(self.area.x0, self.y_baseline());
        common::display(baseline, &self.text, self.font)
    }

    fn paint_center(&self) {
        let baseline = Point::new(self.area.bottom_center().x, self.y_baseline());
        common::display_center(baseline, &self.text, self.font)
    }

    fn paint_right(&self) {
        let baseline = Point::new(self.area.x1, self.y_baseline());
        common::display_right(baseline, &self.text, self.font)
    }
}

impl<T> Component for ChangingTextLine<T>
where
    T: AsRef<str>,
{
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.area = bounds;
        self.pad.place(bounds);
        bounds
    }

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    fn paint(&mut self) {
        self.pad.paint();
        match self.line_alignment {
            LineAlignment::Left => self.paint_left(),
            LineAlignment::Center => self.paint_center(),
            LineAlignment::Right => self.paint_right(),
        }
    }
}

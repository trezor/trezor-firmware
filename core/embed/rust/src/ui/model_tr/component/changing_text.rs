use crate::ui::{
    component::{Component, Event, EventCtx, Never, Pad},
    display::Font,
    geometry::{Alignment, Point, Rect},
};

use super::{common, theme};

/// Component that allows for "allocating" a standalone line of text anywhere
/// on the screen and updating it arbitrarily - without affecting the rest
/// and without being affected by other components.
pub struct ChangingTextLine<T> {
    pad: Pad,
    text: T,
    font: Font,
    /// Whether to show the text. Can be disabled.
    show_content: bool,
    alignment: Alignment,
}

impl<T> ChangingTextLine<T>
where
    T: AsRef<str>,
{
    pub fn new(text: T, font: Font, alignment: Alignment) -> Self {
        Self {
            pad: Pad::with_background(theme::BG),
            text,
            font,
            show_content: true,
            alignment,
        }
    }

    pub fn center_mono(text: T) -> Self {
        Self::new(text, Font::MONO, Alignment::Center)
    }

    pub fn center_bold(text: T) -> Self {
        Self::new(text, Font::BOLD, Alignment::Center)
    }

    // Update the text to be displayed in the line.
    pub fn update_text(&mut self, text: T) {
        self.text = text;
    }

    // Whether we should display the text content.
    // If not, the whole area (Pad) will still be cleared.
    // Is valid until this function is called again.
    pub fn show_or_not(&mut self, show: bool) {
        self.show_content = show;
    }

    /// Gets the height that is needed for this line to fit perfectly
    /// without affecting the rest of the screen.
    /// (Accounting for letters that go below the baseline (y, j, ...).)
    pub fn needed_height(&self) -> i16 {
        self.font.line_height() + 2
    }

    /// Y coordinate of text baseline, is the same for all paints.
    fn y_baseline(&self) -> i16 {
        self.pad.area.y0 + self.font.line_height()
    }

    fn paint_left(&self) {
        let baseline = Point::new(self.pad.area.x0, self.y_baseline());
        common::display(baseline, &self.text, self.font)
    }

    fn paint_center(&self) {
        let baseline = Point::new(self.pad.area.bottom_center().x, self.y_baseline());
        common::display_center(baseline, &self.text, self.font)
    }

    fn paint_right(&self) {
        let baseline = Point::new(self.pad.area.x1, self.y_baseline());
        common::display_right(baseline, &self.text, self.font)
    }
}

impl<T> Component for ChangingTextLine<T>
where
    T: AsRef<str>,
{
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.pad.place(bounds);
        bounds
    }

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    fn paint(&mut self) {
        // Always re-painting from scratch.
        // Effectively clearing the line completely
        // when `self.show_content` is set to `false`.
        self.pad.clear();
        self.pad.paint();
        if self.show_content {
            match self.alignment {
                Alignment::Start => self.paint_left(),
                Alignment::Center => self.paint_center(),
                Alignment::End => self.paint_right(),
            }
        }
    }
}

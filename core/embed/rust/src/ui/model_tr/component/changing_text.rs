use crate::ui::{
    component::{Component, Event, EventCtx, Never, Pad},
    display::Font,
    geometry::{Alignment, Point, Rect},
    util::long_line_content_with_ellipsis,
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
    /// What to show in front of the text if it doesn't fit.
    ellipsis: &'static str,
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
            ellipsis: "...",
            alignment,
        }
    }

    pub fn center_mono(text: T) -> Self {
        Self::new(text, Font::MONO, Alignment::Center)
    }

    pub fn center_bold(text: T) -> Self {
        Self::new(text, Font::BOLD, Alignment::Center)
    }

    /// Not showing ellipsis at the beginning of longer texts.
    pub fn without_ellipsis(mut self) -> Self {
        self.ellipsis = "";
        self
    }

    /// Update the text to be displayed in the line.
    pub fn update_text(&mut self, text: T) {
        self.text = text;
    }

    /// Get current text.
    pub fn get_text(&self) -> &T {
        &self.text
    }

    /// Whether we should display the text content.
    /// If not, the whole area (Pad) will still be cleared.
    /// Is valid until this function is called again.
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

    /// Whether the whole text can be painted in the available space
    fn text_fits_completely(&self) -> bool {
        self.font.text_width(self.text.as_ref()) <= self.pad.area.width()
    }

    fn paint_left(&self) {
        let baseline = Point::new(self.pad.area.x0, self.y_baseline());
        common::display_left(baseline, &self.text, self.font);
    }

    fn paint_center(&self) {
        let baseline = Point::new(self.pad.area.bottom_center().x, self.y_baseline());
        common::display_center(baseline, &self.text, self.font);
    }

    fn paint_right(&self) {
        let baseline = Point::new(self.pad.area.x1, self.y_baseline());
        common::display_right(baseline, &self.text, self.font);
    }

    fn paint_long_content_with_ellipsis(&self) {
        let text_to_display = long_line_content_with_ellipsis(
            self.text.as_ref(),
            self.ellipsis,
            self.font,
            self.pad.area.width(),
        );

        // Creating the notion of motion by shifting the text left and right with
        // each new text character.
        // (So that it is apparent for the user that the text is changing.)
        let x_offset = if self.text.as_ref().len() % 2 == 0 {
            0
        } else {
            2
        };

        let baseline = Point::new(self.pad.area.x0 + x_offset, self.y_baseline());
        common::display_left(baseline, &text_to_display, self.font);
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
            // In the case text cannot fit, show ellipsis and its right part
            if !self.text_fits_completely() {
                self.paint_long_content_with_ellipsis();
            } else {
                match self.alignment {
                    Alignment::Start => self.paint_left(),
                    Alignment::Center => self.paint_center(),
                    Alignment::End => self.paint_right(),
                }
            }
        }
    }
}

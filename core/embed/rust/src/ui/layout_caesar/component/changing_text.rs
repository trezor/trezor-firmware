use crate::{
    strutil::ShortString,
    ui::{
        component::{Component, Event, EventCtx, Never, Pad},
        display::Font,
        geometry::{Alignment, Point, Rect},
        shape::{self, Renderer},
        util::long_line_content_with_ellipsis,
    },
};

use super::theme;

/// Component that allows for "allocating" a standalone line of text anywhere
/// on the screen and updating it arbitrarily - without affecting the rest
/// and without being affected by other components.
pub struct ChangingTextLine {
    pad: Pad,
    text: ShortString,
    font: Font,
    /// Whether to show the text. Can be disabled.
    show_content: bool,
    /// What to show in front of the text if it doesn't fit.
    ellipsis: &'static str,
    alignment: Alignment,
    /// Whether to show the text completely aligned to the top of the bounds
    text_at_the_top: bool,
}

impl ChangingTextLine {
    pub fn new(text: &str, font: Font, alignment: Alignment, max_len: usize) -> Self {
        let text = unwrap!(ShortString::try_from(text));
        debug_assert!(text.capacity() >= max_len);
        Self {
            pad: Pad::with_background(theme::BG),
            text,
            font,
            show_content: true,
            ellipsis: "...",
            alignment,
            text_at_the_top: false,
        }
    }

    pub fn center_mono(text: &str, max_len: usize) -> Self {
        Self::new(text, Font::MONO, Alignment::Center, max_len)
    }

    pub fn center_bold(text: &str, max_len: usize) -> Self {
        Self::new(text, Font::BOLD_UPPER, Alignment::Center, max_len)
    }

    /// Not showing ellipsis at the beginning of longer texts.
    pub fn without_ellipsis(mut self) -> Self {
        self.ellipsis = "";
        self
    }

    /// Showing text at the very top
    pub fn with_text_at_the_top(mut self) -> Self {
        self.text_at_the_top = true;
        self
    }

    /// Update the text to be displayed in the line.
    pub fn update_text(&mut self, text: &str) {
        self.text.clear();
        unwrap!(self.text.push_str(text));
    }

    /// Get current text.
    pub fn get_text(&self) -> &str {
        self.text.as_str()
    }

    /// Changing the current font
    pub fn update_font(&mut self, font: Font) {
        self.font = font;
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
        let y_coord = self.pad.area.y0 + self.font.line_height();
        if self.text_at_the_top {
            // Shifting the text up by 2 pixels.
            y_coord - 2
        } else {
            y_coord
        }
    }

    /// Whether the whole text can be painted in the available space
    fn text_fits_completely(&self) -> bool {
        self.font.text_width(self.text.as_ref()) <= self.pad.area.width()
    }

    fn render_left<'s>(&'s self, target: &mut impl Renderer<'s>) {
        let baseline = Point::new(self.pad.area.x0, self.y_baseline());
        shape::Text::new(baseline, self.text.as_ref())
            .with_font(self.font)
            .render(target);
    }

    fn render_center<'s>(&'s self, target: &mut impl Renderer<'s>) {
        let baseline = Point::new(self.pad.area.bottom_center().x, self.y_baseline());
        shape::Text::new(baseline, self.text.as_ref())
            .with_align(Alignment::Center)
            .with_font(self.font)
            .render(target);
    }

    fn render_right<'s>(&'s self, target: &mut impl Renderer<'s>) {
        let baseline = Point::new(self.pad.area.x1, self.y_baseline());
        shape::Text::new(baseline, self.text.as_ref())
            .with_align(Alignment::End)
            .with_font(self.font)
            .render(target);
    }

    fn render_long_content_with_ellipsis<'s>(&'s self, target: &mut impl Renderer<'s>) {
        let text_to_display = long_line_content_with_ellipsis(
            self.text.as_ref(),
            self.ellipsis,
            self.font,
            self.pad.area.width(),
        );

        // Creating the notion of motion by shifting the text left and right with
        // each new text character.
        // (So that it is apparent for the user that the text is changing.)
        let x_offset = if self.text.len() % 2 == 0 { 0 } else { 2 };

        let baseline = Point::new(self.pad.area.x0 + x_offset, self.y_baseline());
        shape::Text::new(baseline, &text_to_display)
            .with_font(self.font)
            .render(target);
    }
}

impl Component for ChangingTextLine {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.pad.place(bounds);
        bounds
    }

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.pad.render(target);
        if self.show_content {
            // In the case text cannot fit, show ellipsis and its right part
            if !self.text_fits_completely() {
                self.render_long_content_with_ellipsis(target);
            } else {
                match self.alignment {
                    Alignment::Start => self.render_left(target),
                    Alignment::Center => self.render_center(target),
                    Alignment::End => self.render_right(target),
                }
            }
        }
    }
}

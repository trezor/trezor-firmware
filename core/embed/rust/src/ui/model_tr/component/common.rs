use heapless::String;

use crate::util;

use crate::ui::{display, geometry::Point};

use super::theme;

const MIDDLE_ROW: i32 = 72;

/// Display bold white text on black background
pub fn display_bold(baseline: Point, text: &str) {
    display::text(baseline, text, theme::FONT_BOLD, theme::FG, theme::BG);
}

/// Display bold white text on black background,
/// centered around a baseline Point
pub fn display_bold_center(baseline: Point, text: &str) {
    display::text_center(baseline, text, theme::FONT_BOLD, theme::FG, theme::BG);
}

/// Display bold white text on black background,
/// with right boundary at a baseline Point
pub fn display_bold_right(baseline: Point, text: &str) {
    display::text_right(baseline, text, theme::FONT_BOLD, theme::FG, theme::BG);
}

/// Component that can be used as a choice item.
/// Allows to have a choice of anything that can be painted on screen.
pub trait ChoiceItem {
    fn paint_center(&mut self);
    fn paint_left(&mut self);
    fn paint_right(&mut self);
}

/// String component used as a choice item.
pub struct StringChoiceItem {
    // Arbitrary chosen. TODO: agree on this
    text: String<50>,
}

impl StringChoiceItem {
    pub fn from_slice(slice: &str) -> Self {
        let text = String::from(slice);
        Self { text }
    }

    pub fn from_char(ch: char) -> Self {
        let text = util::char_to_string(ch);
        Self { text }
    }
}

impl ChoiceItem for StringChoiceItem {
    fn paint_center(&mut self) {
        // Displaying the center choice lower than the rest,
        // to make it more clear this is the current choice
        // (and also the left and right ones do not collide with it)
        display_bold_center(Point::new(64, MIDDLE_ROW + 10), self.text.as_str());
    }

    fn paint_left(&mut self) {
        display_bold(Point::new(5, MIDDLE_ROW), self.text.as_str());
    }

    fn paint_right(&mut self) {
        display_bold_right(Point::new(123, MIDDLE_ROW), self.text.as_str());
    }
}

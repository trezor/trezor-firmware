use crate::ui::{
    display::{self, Font},
    geometry::Point,
};

use super::theme;

/// Display white text on black background
pub fn display_left<T: AsRef<str>>(baseline: Point, text: T, font: Font) {
    display::text_left(baseline, text.as_ref(), font, theme::FG, theme::BG);
}

/// Display black text on white background
pub fn display_inverse<T: AsRef<str>>(baseline: Point, text: T, font: Font) {
    display::text_left(baseline, text.as_ref(), font, theme::BG, theme::FG);
}

/// Display white text on black background,
/// centered around a baseline Point
pub fn display_center<T: AsRef<str>>(baseline: Point, text: T, font: Font) {
    display::text_center(baseline, text.as_ref(), font, theme::FG, theme::BG);
}

/// Display white text on black background,
/// with right boundary at a baseline Point
pub fn display_right<T: AsRef<str>>(baseline: Point, text: T, font: Font) {
    display::text_right(baseline, text.as_ref(), font, theme::FG, theme::BG);
}

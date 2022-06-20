use crate::ui::{display, geometry::Point};

use super::theme;

/// Display bold white text on black background
pub fn display_text(baseline: Point, text: &str) {
    display::text(baseline, text, theme::FONT_BOLD, theme::FG, theme::BG);
}

/// Display bold white text on black background, centered around a baseline
/// Point
pub fn display_text_center(baseline: Point, text: &str) {
    display::text_center(baseline, text, theme::FONT_BOLD, theme::FG, theme::BG);
}

/// Display bold white text on black background, with right boundary at a
/// baseline Point
pub fn display_text_right(baseline: Point, text: &str) {
    display::text_right(baseline, text, theme::FONT_BOLD, theme::FG, theme::BG);
}

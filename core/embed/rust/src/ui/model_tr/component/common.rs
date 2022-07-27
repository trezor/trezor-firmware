use crate::ui::{display, geometry::Point};

use super::theme;

/// Helper to unite the row height.
pub fn row_height_bold() -> i32 {
    // It never reaches the maximum height
    theme::FONT_BOLD.line_height() - 2
}

/// Display header text.
pub fn display_header(baseline: Point, text: &str) {
    display::text(baseline, text, theme::FONT_HEADER, theme::FG, theme::BG);
}

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

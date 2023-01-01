use crate::ui::{
    display::{self, Font},
    geometry::{Offset, Point, Rect},
};

use super::theme;

/// Display white text on black background
pub fn display<T: AsRef<str>>(baseline: Point, text: &T, font: Font) {
    display::text_left(baseline, text.as_ref(), font, theme::FG, theme::BG);
}

/// Display black text on white background
pub fn display_inverse<T: AsRef<str>>(baseline: Point, text: &T, font: Font) {
    display::text_left(baseline, text.as_ref(), font, theme::BG, theme::FG);
}

/// Display white text on black background,
/// centered around a baseline Point
pub fn display_center<T: AsRef<str>>(baseline: Point, text: &T, font: Font) {
    display::text_center(baseline, text.as_ref(), font, theme::FG, theme::BG);
}

/// Display white text on black background,
/// with right boundary at a baseline Point
pub fn display_right<T: AsRef<str>>(baseline: Point, text: &T, font: Font) {
    display::text_right(baseline, text.as_ref(), font, theme::FG, theme::BG);
}

/// Display title/header at the top left of the given area.
/// Returning the painted height of the whole header.
pub fn paint_header_left<T: AsRef<str>>(title: T, area: Rect) -> i16 {
    let text_heigth = theme::FONT_HEADER.text_height();
    let title_baseline = area.top_left() + Offset::y(text_heigth);
    display::text_left(
        title_baseline,
        title.as_ref(),
        theme::FONT_HEADER,
        theme::FG,
        theme::BG,
    );
    text_heigth
}

/// Display title/header centered at the top of the given area.
/// Returning the painted height of the whole header.
pub fn paint_header_centered<T: AsRef<str>>(title: T, area: Rect) -> i16 {
    let text_heigth = theme::FONT_HEADER.text_height();
    let title_baseline = area.top_center() + Offset::y(text_heigth);
    display::text_center(
        title_baseline,
        title.as_ref(),
        theme::FONT_HEADER,
        theme::FG,
        theme::BG,
    );
    text_heigth
}

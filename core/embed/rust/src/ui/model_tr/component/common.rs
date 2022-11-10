use crate::ui::{
    display::{self, Font, Icon},
    geometry::{Offset, Point, Rect},
};

use heapless::String;

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

const MAX_VISIBLE_CHARS: usize = 18;
const TOP_ROW_TEXT: i16 = 7;

/// Display indication of current user input - PIN, passphrase etc.
/// Showing one asterisk for each character of the input.
pub fn display_dots_center_top(dots_amount: usize, offset_from_top: i16) {
    let y_position = TOP_ROW_TEXT + offset_from_top;
    let dots_visible = dots_amount.min(MAX_VISIBLE_CHARS);

    // String::repeat() is not available for heapless::String
    let mut dots: String<MAX_VISIBLE_CHARS> = String::new();
    for _ in 0..dots_visible {
        dots.push_str("*").unwrap();
    }

    // Giving some notion of change even for longer-than-visible passphrases
    // - slightly shifting the dots to the left and right after each new digit
    if dots_amount > MAX_VISIBLE_CHARS && dots_amount % 2 == 0 {
        display_center(Point::new(61, y_position), &dots, Font::MONO);
    } else {
        display_center(Point::new(64, y_position), &dots, Font::MONO);
    }
}

/// Display secret input that user is currently doing - PIN, passphrase etc.
pub fn display_secret_center_top<T: AsRef<str>>(secret: T, offset_from_top: i16) {
    let y_position = TOP_ROW_TEXT + offset_from_top;
    let char_amount = secret.as_ref().len();
    if char_amount <= MAX_VISIBLE_CHARS {
        display_center(Point::new(64, y_position), &secret, Font::MONO);
    } else {
        // Show the last part with preceding ellipsis to show something is hidden
        let ellipsis = "...";
        let offset: usize = char_amount.saturating_sub(MAX_VISIBLE_CHARS) + ellipsis.len();
        let to_show = build_string!(MAX_VISIBLE_CHARS, ellipsis, &secret.as_ref()[offset..]);
        display_center(Point::new(64, y_position), &to_show, Font::MONO);
    }
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

/// Draws icon and text on the same line - icon on the left.
pub fn icon_with_text<T: AsRef<str>>(baseline: Point, icon: Icon, text: T, font: Font) {
    icon.draw_bottom_left(baseline, theme::FG, theme::BG);
    let text_x_offset = icon.width() + 2;
    display(baseline + Offset::x(text_x_offset), &text.as_ref(), font);
}

/// Draw two lines - icon with label text (key) and another text (value) below.
/// Returns the height painted below the given baseline.
pub fn key_value_icon<T: AsRef<str>>(
    baseline: Point,
    icon: Icon,
    label: T,
    label_font: Font,
    value: T,
    value_font: Font,
) -> i16 {
    icon_with_text(baseline, icon, label, label_font);
    let line_height = value_font.line_height();
    let next_line = baseline + Offset::y(line_height);
    display(next_line, &value, value_font);
    line_height
}

use crate::ui::{
    display::{self, Font},
    geometry::Point,
};

use heapless::String;

use super::theme;

/// Display header text.
pub fn display_header(baseline: Point, text: &str) {
    // TODO: make this centered?
    display::text(baseline, text, theme::FONT_HEADER, theme::FG, theme::BG);
}

/// Display bold white text on black background
pub fn display(baseline: Point, text: &str, font: Font) {
    display::text(baseline, text, font, theme::FG, theme::BG);
}

/// Display white text on black background,
/// centered around a baseline Point
pub fn display_center(baseline: Point, text: &str, font: Font) {
    display::text_center(baseline, text, font, theme::FG, theme::BG);
}

/// Display white text on black background,
/// with right boundary at a baseline Point
pub fn display_right(baseline: Point, text: &str, font: Font) {
    display::text_right(baseline, text, font, theme::FG, theme::BG);
}

/// Display magnified normal font white text on black background,
/// with left bottom at a baseline point.
pub fn display_magnified(ch: char, magnified: u8, baseline: Point) {
    theme::FONT_NORMAL.display_char_magnified(ch, magnified, baseline, theme::FG, theme::BG);
}

const MAX_VISIBLE_CHARS: usize = 18;
const TOP_ROW_TEXT: i32 = 7;

/// Display indication of current user input - PIN, passphrase etc.
/// Showing one asterisk for each character of the input.
pub fn display_dots_center_top(dots_amount: usize, offset_from_top: i32) {
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
        display_center(Point::new(61, y_position), &dots, theme::FONT_MONO);
    } else {
        display_center(Point::new(64, y_position), &dots, theme::FONT_MONO);
    }
}

/// Display secret input that user is currently doing - PIN, passphrase etc.
pub fn display_secret_center_top(secret: &str, offset_from_top: i32) {
    let y_position = TOP_ROW_TEXT + offset_from_top;
    let char_amount = secret.len();
    if char_amount <= MAX_VISIBLE_CHARS {
        display_center(Point::new(64, y_position), secret, theme::FONT_MONO);
    } else {
        // Show the last part with preceding ellipsis to show something is hidden
        let ellipsis = "...";
        let offset: usize = char_amount.saturating_sub(MAX_VISIBLE_CHARS) + ellipsis.len();
        let to_show = build_string!(MAX_VISIBLE_CHARS, ellipsis, &secret[offset..]);
        display_center(Point::new(64, y_position), &to_show, theme::FONT_MONO);
    }
}

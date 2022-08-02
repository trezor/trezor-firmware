use crate::ui::{
    display::{self, Font, Icon},
    geometry::{Offset, Point},
    model_tr::constant,
};

use heapless::String;

use super::theme;

/// Display header text.
pub fn display_header<T: AsRef<str>>(baseline: Point, text: T) {
    // TODO: make this centered?
    display::text(
        baseline,
        text.as_ref(),
        theme::FONT_HEADER,
        theme::FG,
        theme::BG,
    );
}

/// Display bold white text on black background
pub fn display<T: AsRef<str>>(baseline: Point, text: T, font: Font) {
    display::text(baseline, text.as_ref(), font, theme::FG, theme::BG);
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
        display_center(Point::new(61, y_position), dots, theme::FONT_MONO);
    } else {
        display_center(Point::new(64, y_position), dots, theme::FONT_MONO);
    }
}

/// Display secret input that user is currently doing - PIN, passphrase etc.
pub fn display_secret_center_top<T: AsRef<str>>(secret: T, offset_from_top: i32) {
    let y_position = TOP_ROW_TEXT + offset_from_top;
    let char_amount = secret.as_ref().len();
    if char_amount <= MAX_VISIBLE_CHARS {
        display_center(Point::new(64, y_position), secret, theme::FONT_MONO);
    } else {
        // Show the last part with preceding ellipsis to show something is hidden
        let ellipsis = "...";
        let offset: usize = char_amount.saturating_sub(MAX_VISIBLE_CHARS) + ellipsis.len();
        let to_show = build_string!(MAX_VISIBLE_CHARS, ellipsis, &secret.as_ref()[offset..]);
        display_center(Point::new(64, y_position), to_show, theme::FONT_MONO);
    }
}

/// Display title and possible subtitle together with a dotted line spanning
/// the entire width.
/// Returning the painted height of the whole header.
pub fn paint_header<T: AsRef<str>>(top_left: Point, title: T, subtitle: Option<T>) -> i32 {
    let text_heigth = theme::FONT_HEADER.text_height();
    let title_baseline = top_left + Offset::y(text_heigth);
    display_header(title_baseline, title);
    // Optionally painting the subtitle as well
    // (and offsetting the dotted line in that case)
    let mut dotted_line_offset = text_heigth + 2;
    if let Some(subtitle) = subtitle {
        dotted_line_offset += text_heigth;
        display_header(title_baseline + Offset::y(text_heigth), subtitle);
    }
    let line_start = top_left + Offset::y(dotted_line_offset);
    display::dotted_line(line_start, constant::WIDTH, theme::FG);
    dotted_line_offset
}

/// Draws icon and text on the same line - icon on the left.
pub fn icon_with_text<T: AsRef<str>>(baseline: Point, icon: Icon<T>, text: T, font: Font) {
    icon.draw_bottom_left(baseline, theme::FG, theme::BG);
    let text_x_offset = icon.width() + 2;
    display(baseline + Offset::x(text_x_offset), text.as_ref(), font);
}

/// Draw two lines - icon with label text (key) and another text (value) below.
/// Returns the height painted below the given baseline.
pub fn key_value_icon<T: AsRef<str>>(
    baseline: Point,
    icon: Icon<T>,
    label_text: T,
    label_font: Font,
    key_text: T,
    key_font: Font,
) -> i32 {
    icon_with_text(baseline, icon, label_text, label_font);
    let line_height = key_font.text_height();
    let next_line = baseline + Offset::y(line_height);
    display(next_line, key_text, key_font);
    line_height
}

use crate::ui::{
    component::text::TextStyle,
    display,
    geometry::{Offset, Point},
};

use heapless::String;

use super::display::Font;

pub trait ResultExt {
    fn assert_if_debugging_ui(self, message: &str);
}

impl<T, E> ResultExt for Result<T, E> {
    fn assert_if_debugging_ui(self, #[allow(unused)] message: &str) {
        #[cfg(feature = "ui_debug")]
        if self.is_err() {
            panic!("{}", message);
        }
    }
}

pub fn u32_to_str(num: u32, buffer: &mut [u8]) -> Option<&str> {
    let mut i = 0;
    let mut num = num;

    while num > 0 && i < buffer.len() {
        buffer[i] = b'0' + ((num % 10) as u8);
        num /= 10;
        i += 1;
    }
    match i {
        0 => Some("0"),
        _ if num > 0 => None,
        _ => {
            let result = &mut buffer[..i];
            result.reverse();
            Some(core::str::from_utf8(result).unwrap())
        }
    }
}

#[cfg(feature = "ui_debug")]
static mut DISABLE_ANIMATION: bool = false;

#[cfg(feature = "ui_debug")]
pub fn animation_disabled() -> bool {
    // SAFETY: single-threaded access
    unsafe { DISABLE_ANIMATION }
}

#[cfg(feature = "ui_debug")]
pub fn set_animation_disabled(disabled: bool) {
    // SAFETY: single-threaded access
    unsafe {
        DISABLE_ANIMATION = disabled;
    }
}

#[cfg(not(feature = "ui_debug"))]
pub fn animation_disabled() -> bool {
    false
}

#[cfg(not(feature = "ui_debug"))]
pub fn set_animation_disabled(_disabled: bool) {}

/// Display an icon and a text centered relative to given `Point`.
pub fn icon_text_center(
    baseline: Point,
    icon: &'static [u8],
    space: i16,
    text: &str,
    style: TextStyle,
    text_offset: Offset,
) {
    let toif_info = unwrap!(display::toif_info(icon), "Invalid TOIF data");
    let icon_width = toif_info.0.y;
    let text_width = style.text_font.text_width(text);
    let text_height = style.text_font.text_height();
    let text_center = baseline + Offset::new((icon_width + space) / 2, text_height / 2);
    let icon_center = baseline - Offset::x((text_width + space) / 2);

    display::text_center(
        text_center + text_offset,
        text,
        style.text_font,
        style.text_color,
        style.background_color,
    );
    display::icon(icon_center, icon, style.text_color, style.background_color);
}

/// Convert char to a String of chosen length.
pub fn char_to_string<const L: usize>(ch: char) -> String<L> {
    let mut s = String::new();
    s.push(ch).unwrap();
    s
}

/// Returns text to be fit on one line of a given length.
/// When the text is too long to fit, it is truncated with ellipsis
/// on the left side.
// Hardcoding 50 as the length of the returned String - there should
// not be any lines as long as this.
pub fn long_line_content_with_ellipsis(
    text: &str,
    ellipsis: &str,
    text_font: Font,
    available_width: i16,
) -> String<50> {
    if text_font.text_width(text) <= available_width {
        String::from(text) // whole text can fit
    } else {
        // Text is longer, showing its right end with ellipsis at the beginning.
        // Finding out how many additional text characters will fit in,
        // starting from the right end.
        let ellipsis_width = text_font.text_width(ellipsis);
        let remaining_available_width = available_width - ellipsis_width;
        let chars_from_right = text_font.longest_suffix(remaining_available_width, text);

        build_string!(50, ellipsis, &text[text.len() - chars_from_right..])
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn u32_to_str_valid() {
        let testcases = [0, 1, 9, 10, 11, 999, u32::MAX];
        let mut b = [0; 10];

        for test in testcases {
            let converted = u32_to_str(test, &mut b).unwrap();
            let s = test.to_string();
            assert_eq!(converted, s);
        }
    }

    #[test]
    fn u32_to_str_small_buffer() {
        let testcases = [1000, 31337, u32::MAX];
        let mut b = [0; 3];

        for test in testcases {
            let converted = u32_to_str(test, &mut b);
            assert_eq!(converted, None)
        }
    }
}

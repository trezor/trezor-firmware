use crate::strutil::ShortString;

use super::display::Font;

pub trait ResultExt {
    fn assert_if_debugging_ui(self, message: &str);
}

impl<T, E> ResultExt for Result<T, E> {
    fn assert_if_debugging_ui(self, #[allow(unused)] message: &str) {
        #[cfg(feature = "ui_debug")]
        if self.is_err() {
            fatal_error!(message);
        }
    }
}

/// Constructs a string from a C string.
///
/// # Safety
///
/// The caller is responsible that the pointer is valid, which means that:
/// (a) it points to a memory containing a valid C string (zero-terminated
/// sequence of characters), and
/// (b) that the pointer has appropriate lifetime.
pub unsafe fn from_c_str<'a>(c_str: *const cty::c_char) -> Option<&'a str> {
    if c_str.is_null() {
        return None;
    }
    unsafe {
        let bytes = core::ffi::CStr::from_ptr(c_str as _).to_bytes();
        if bytes.is_ascii() {
            Some(core::str::from_utf8_unchecked(bytes))
        } else {
            None
        }
    }
}

/// Construct str from a C array.
///
/// # Safety
///
/// The caller is responsible that the pointer is valid, which means that:
/// (a) it points to a memory containing array of characters, with length `len`,
/// and
/// (b) that the pointer has appropriate lifetime.
pub unsafe fn from_c_array<'a>(c_str: *const cty::c_char, len: usize) -> Option<&'a str> {
    if c_str.is_null() {
        return None;
    }
    unsafe {
        let slice = core::slice::from_raw_parts(c_str as *const u8, len);
        if slice.is_ascii() {
            Some(core::str::from_utf8_unchecked(slice))
        } else {
            None
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

/// Convert char to a ShortString.
pub fn char_to_string(ch: char) -> ShortString {
    let mut s = ShortString::new();
    unwrap!(s.push(ch));
    s
}

/// Splits `text` in two lines:
/// the first line has to fit in the `available_width`,
/// while the 2nd line contains the rest of the text.
pub fn split_two_lines(text: &str, text_font: Font, available_width: i16) -> (&str, &str) {
    let p = text_font.longest_prefix(available_width, text);
    let (first_line, second_line) = if p.is_empty() {
        // If we cannot find a space to split on, we won't split at all.
        // It is the caller's responsibility to deal with the extra long 2nd line.
        // (Remember, 2nd line can always be longer than the width, anyway!)
        ("", text)
    } else {
        (p, text[p.len()..].trim())
    };

    #[cfg(feature = "ui_debug")]
    if text_font.text_width(second_line) > available_width {
        fatal_error!(&uformat!(len: 128, "Text too long: '{}'", text));
    }

    (first_line, second_line)
}

/// Returns text to be fit on one line of a given length.
/// When the text is too long to fit, it is truncated with ellipsis
/// on the left side.
/// This assumes no lines are longer than 50 chars (ShortString limit)
pub fn long_line_content_with_ellipsis(
    text: &str,
    ellipsis: &str,
    text_font: Font,
    available_width: i16,
) -> ShortString {
    if text_font.text_width(text) <= available_width {
        unwrap!(ShortString::try_from(text)) // whole text can fit
    } else {
        // Text is longer, showing its right end with ellipsis at the beginning.
        // Finding out how many additional text characters will fit in,
        // starting from the right end.
        let ellipsis_width = text_font.text_width(ellipsis);
        let remaining_available_width = available_width - ellipsis_width;
        let chars_from_right = text_font.longest_suffix(remaining_available_width, text);

        let mut s = ShortString::new();
        unwrap!(s.push_str(ellipsis));
        unwrap!(s.push_str(&text[text.len() - chars_from_right..]));
        s
    }
}

/// Create the `Icon` constant with given name and path.
macro_rules! include_icon {
    ($name:ident, $path:expr) => {
        pub const $name: $crate::ui::display::toif::Icon =
            $crate::ui::display::toif::Icon::debug_named(
                $crate::ui::util::include_res!($path),
                stringify!($name),
            );
    };
}

pub(crate) use include_icon;

macro_rules! include_res {
    ($filename:expr) => {
        include_bytes!(concat!(env!("CARGO_MANIFEST_DIR"), "/src/ui/", $filename))
    };
}
pub(crate) use include_res;

/// Pager helper for keeping track of the current page and total number of
/// pages.
///
/// Page numbers are zero-based, so the values can be directly used for indexing
/// arrays, etc. It always holds that `current < total`, and `total > 0`.
#[derive(Clone, Copy, PartialEq, Eq)]
#[cfg_attr(feature = "debug", derive(ufmt::derive::uDebug))]
pub struct Pager {
    /// Zero-based index of the current page.
    current: u16,
    /// Total number of pages.
    total: u16,
}

impl Pager {
    /// Create a new pager with the given total number of pages.
    pub fn new(total: u16) -> Self {
        debug_assert!(total > 0);
        Self { current: 0, total }
    }

    /// Create a new pager with a single page.
    pub fn single_page() -> Self {
        Self::new(1)
    }

    /// Create a new pager with the given current page index.
    pub fn with_current(mut self, current: u16) -> Self {
        self.set_current(current);
        self
    }

    /// Limit the size of the pager to the given number of pages.
    pub fn with_limit(mut self, limit: u16) -> Self {
        self.total = self.total.min(limit);
        // update current to be within bounds
        self.set_current(self.current);
        self
    }

    /// Get the current page index.
    pub fn current(&self) -> u16 {
        self.current
    }

    /// Get the total number of pages.
    pub fn total(&self) -> u16 {
        self.total
    }

    /// Set the current page index.
    pub fn set_current(&mut self, idx: u16) {
        self.current = idx.min(self.last());
    }

    /// Get the last page index.
    pub fn last(&self) -> u16 {
        self.total.saturating_sub(1)
    }

    /// Check if the current page is the first one.
    pub fn is_first(&self) -> bool {
        self.current == 0
    }

    /// Check if the current page is the last one.
    pub fn is_last(&self) -> bool {
        self.current == self.last()
    }

    /// Check if the pager has a single page.
    pub fn is_single(&self) -> bool {
        self.total == 1
    }

    /// Check if there is a previous page for the current page.
    pub fn has_prev(&self) -> bool {
        !self.is_first()
    }

    /// Check if there is a next page for the current page.
    pub fn has_next(&self) -> bool {
        !self.is_last()
    }

    /// Get the index of the next page.
    pub fn next(&self) -> u16 {
        self.current.saturating_add(1).min(self.last())
    }

    /// Get the index of the previous page.
    pub fn prev(&self) -> u16 {
        self.current.saturating_sub(1)
    }

    /// Go to the next page.
    ///
    /// Returns true if this resulted in a move. False if we are already at the
    /// last page.
    pub fn goto_next(&mut self) -> bool {
        let has_next = self.has_next();
        self.current = self.next();
        has_next
    }

    /// Go to the previous page.
    ///
    /// Returns true if this resulted in a move. False if we are already at the
    /// first page.
    pub fn goto_prev(&mut self) -> bool {
        let has_prev = self.has_prev();
        self.current = self.prev();
        has_prev
    }

    /// Go to the first page.
    pub fn goto_first(&mut self) {
        self.current = 0;
    }

    /// Go to the last page.
    pub fn goto_last(&mut self) {
        self.current = self.last();
    }
}

impl Default for Pager {
    fn default() -> Self {
        Self::single_page()
    }
}

#[cfg(test)]
mod tests {
    use crate::strutil;

    #[test]
    fn u32_to_str_valid() {
        let testcases = [0, 1, 9, 10, 11, 999, u32::MAX];
        let mut b = [0; 10];

        for test in testcases {
            let converted = strutil::format_i64(test as i64, &mut b).unwrap();
            let s = test.to_string();
            assert_eq!(converted, s);
        }
    }

    #[test]
    fn u32_to_str_small_buffer() {
        let testcases = [1000, 31337, u32::MAX];
        let mut b = [0; 3];

        for test in testcases {
            let converted = strutil::format_i64(test as i64, &mut b);
            assert_eq!(converted, None)
        }
    }
}

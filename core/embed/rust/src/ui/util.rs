use heapless::String;

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

/// Convert char to a String of chosen length.
pub fn char_to_string<const L: usize>(ch: char) -> String<L> {
    let mut s = String::new();
    s.push(ch).unwrap();
    s
}

/// Return the beginning and end of the given text with ellipsis in between.
pub fn ellipsise_text<T: AsRef<str>, const N: usize>(
    text: T,
    chars_to_show: usize,
    ellipsis: &str,
) -> String<N> {
    let len = text.as_ref().len();
    let start = &text.as_ref()[0..chars_to_show];
    let end = &text.as_ref()[(len - chars_to_show)..len];
    build_string!(N, start, ellipsis, end)
}

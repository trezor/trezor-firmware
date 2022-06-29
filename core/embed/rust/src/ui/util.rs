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

pub fn char_to_string<const L: usize>(ch: char) -> String<L> {
    let mut s = String::new();
    s.push(ch).unwrap();
    s
}

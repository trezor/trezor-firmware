use heapless::String;

#[cfg(feature = "model_tr")]
use crate::ui::model_tr::component::ButtonPos;

/// Visitor passed into `Trace` types.
pub trait Tracer {
    fn int(&mut self, i: i64);
    fn bytes(&mut self, b: &[u8]);
    fn string(&mut self, s: &str);
    fn symbol(&mut self, name: &str);
    fn open(&mut self, name: &str);
    fn field(&mut self, name: &str, value: &dyn Trace);
    fn title(&mut self, title: &str);
    fn button(&mut self, button: &str);
    fn content_flag(&mut self);
    fn kw_pair(&mut self, key: &str, value: &dyn Trace);
    fn close(&mut self);
}

// Identifiers for tagging various parts of the Trace
// message - so that things like title or the main screen
// content can be read in debug mode by micropython.
pub const TITLE_TAG: &str = " **TITLE** ";
pub const BTN_TAG: &str = " **BTN** ";
pub const CONTENT_TAG: &str = " **CONTENT** ";
// For when the button is not used
pub const EMPTY_BTN: &str = "---";

/// Value that can describe own structure and data using the `Tracer` interface.
pub trait Trace {
    fn trace(&self, t: &mut dyn Tracer);
    /// Describes what happens when a certain button is triggered.
    #[cfg(feature = "model_tr")]
    fn get_btn_action(&self, _pos: ButtonPos) -> String<25> {
        "Default".into()
    }
    /// Report actions for all three buttons in easy-to-parse format.
    #[cfg(feature = "model_tr")]
    fn report_btn_actions(&self, t: &mut dyn Tracer) {
        t.kw_pair("left_action", &self.get_btn_action(ButtonPos::Left));
        t.kw_pair("middle_action", &self.get_btn_action(ButtonPos::Middle));
        t.kw_pair("right_action", &self.get_btn_action(ButtonPos::Right));
    }
}

impl Trace for &[u8] {
    fn trace(&self, t: &mut dyn Tracer) {
        t.bytes(self);
    }
}

impl<const N: usize> Trace for &[u8; N] {
    fn trace(&self, t: &mut dyn Tracer) {
        t.bytes(&self[..])
    }
}

impl<const N: usize> Trace for String<N> {
    fn trace(&self, t: &mut dyn Tracer) {
        t.string(&self[..])
    }
}

impl Trace for &str {
    fn trace(&self, t: &mut dyn Tracer) {
        t.string(self);
    }
}

impl Trace for usize {
    fn trace(&self, t: &mut dyn Tracer) {
        t.int(*self as i64);
    }
}

impl<T> Trace for Option<T>
where
    T: Trace,
{
    fn trace(&self, d: &mut dyn Tracer) {
        match self {
            Some(v) => v.trace(d),
            None => d.symbol("None"),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    impl Tracer for Vec<u8> {
        fn int(&mut self, i: i64) {
            self.string(&i.to_string());
        }

        fn bytes(&mut self, b: &[u8]) {
            self.extend(b)
        }

        fn string(&mut self, s: &str) {
            self.extend(s.as_bytes())
        }

        fn symbol(&mut self, name: &str) {
            self.string("<");
            self.string(name);
            self.string(">");
        }

        fn open(&mut self, name: &str) {
            self.string("<");
            self.string(name);
            self.string(" ");
        }

        fn field(&mut self, name: &str, value: &dyn Trace) {
            self.string(name);
            self.string(":");
            value.trace(self);
            self.string(" ");
        }

        /// Mark the string as a title/header.
        fn title(&mut self, title: &str) {
            self.string(TITLE_TAG);
            self.string(title);
            self.string(TITLE_TAG);
        }

        /// Mark the string as a button content.
        fn button(&mut self, button: &str) {
            self.string(BTN_TAG);
            self.string(button);
            self.string(BTN_TAG);
        }

        // Mark the following as content visible on the screen,
        // until it is called next time.
        fn content_flag(&mut self) {
            self.string(CONTENT_TAG);
        }

        /// Key-value pair for easy parsing
        fn kw_pair(&mut self, key: &str, value: &dyn Trace) {
            self.string(key);
            self.string("::");
            value.trace(self);
            self.string(","); // mostly for human readability
        }

        fn close(&mut self) {
            self.string(">")
        }
    }
}

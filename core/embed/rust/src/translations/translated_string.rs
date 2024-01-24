use crate::strutil::TString;

use super::blob::Translations;
pub use super::generated::translated_string::TranslatedString;

impl TranslatedString {
    pub(super) fn translate<'a>(self, source: Option<&'a Translations>) -> &'a str {
        source
            .and_then(|s| s.translation(self as _))
            .unwrap_or(self.untranslated())
    }

    pub fn map_translated<F, T>(self, fun: F) -> T
    where
        F: for<'a> FnOnce(&'a str) -> T,
        T: 'static,
    {
        // SAFETY: The bound on F _somehow_ ensures that the reference cannot escape
        // the closure. (I don't understand how, but it does), see soundness test below.
        // For good measure, we limit the return value to 'static.
        let translations = unsafe { super::flash::get() };
        fun(self.translate(translations))
    }

    pub const fn as_tstring(self) -> TString<'static> {
        TString::Translation(self)
    }
}

// #[cfg(test)]
// mod tests {
//     use super::TranslatedString;

//     #[test]
//     fn test_soundness() {
//         let tr = TranslatedString::address__public_key;
//         let mut opt: Option<&str> = None;
//         tr.map_translated(|s| opt = Some(s));
//         assert!(matches!(opt, Some("Address / Public key")));
//     }
// }

use crate::strutil::TString;

use super::blob::Translations;
pub use super::generated::translated_string::TranslatedString;

impl TranslatedString {
    pub fn translate<'a>(self, source: Option<&'a Translations>) -> &'a str {
        source
            .and_then(|s| s.translation(self as _))
            .unwrap_or(self.untranslated())
    }

    /// Maps the translated string to a value using a closure.
    ///
    /// # Safety
    ///
    /// This is the only safe way to access a reference to the flash data. This
    /// function guarantees that the reference is valid throughout the
    /// closure, but as soon as the closure returns, the lock held on flash
    /// data is released. This means that translations could get deinited
    /// and rewritten, invalidating the reference.
    ///
    /// To guarantee that the reference does not escape the closure, we use a
    /// HRTB of the closure's argument, which ensures that the lifetime of
    /// the reference is too short to store it outside in any form.
    pub fn map_translated<F, T>(self, fun: F) -> T
    where
        F: for<'a> FnOnce(&'a str) -> T,
    {
        let translations = unwrap!(super::flash::get());
        fun(self.translate(translations.as_ref()))
    }

    pub const fn as_tstring(self) -> TString<'static> {
        TString::from_translation(self)
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

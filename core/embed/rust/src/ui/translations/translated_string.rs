pub use super::generated::translated_string::TranslatedString;
use super::Translations;

impl TranslatedString {
    pub fn translate<'a>(self, source: Option<&'a Translations>) -> &'a str {
        source
            .and_then(|s| s.translation(self as _))
            .unwrap_or(self.untranslated())
    }
}

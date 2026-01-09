use crate::strutil::TString;

use super::blob::Translations;
pub use super::generated::translated_string::TranslatedString;

#[cfg(feature = "micropython")]
use crate::micropython::qstr::Qstr;

impl TranslatedString {
    pub(super) fn untranslated(self) -> &'static str {
        for blob in Self::BLOBS {
            // `offsets` must be sorted by its first element
            let index = match blob.offsets.binary_search_by(|(key, _)| key.cmp(&self)) {
                Ok(index) => index,
                Err(_) => continue,
            };
            let start_offset = index
                .checked_sub(1)
                .map_or(0, |prev_index| blob.offsets[prev_index].1);
            let end_offset = blob.offsets[index].1;
            return &blob.text[start_offset.into()..end_offset.into()];
        }
        fatal_error!("not found");
    }

    pub fn translate<'a>(self, source: Option<&'a Translations>) -> &'a str {
        source
            .and_then(|s| s.translation(self as _))
            .unwrap_or(self.untranslated())
    }

    #[cfg(feature = "micropython")]
    pub(super) fn from_qstr(qstr: Qstr) -> Option<Self> {
        // QSTR_MAP must be sorted by its first element
        match Self::QSTR_MAP.binary_search_by(|(key, _)| key.to_u16().cmp(&qstr.to_u16())) {
            Ok(index) => Some(Self::QSTR_MAP[index].1),
            Err(_) => None,
        }
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

#[cfg(test)]
mod test {
    use super::*;

    #[test]
    fn test_sorted_qstr_map() {
        for pair in TranslatedString::QSTR_MAP.windows(2) {
            assert!(pair[0].0.to_u16() < pair[1].0.to_u16())
        }
    }

    #[test]
    fn test_sorted_offsets() {
        for blob in TranslatedString::BLOBS {
            for pair in blob.offsets.windows(2) {
                assert!(pair[0].0 < pair[1].0)
            }
        }
    }

    #[test]
    fn test_lookup_untranslated_text() {
        for blob in TranslatedString::BLOBS {
            let mut prev_offset = 0;
            for &(name, offset) in blob.offsets {
                let expected = &blob.text[prev_offset.into()..offset.into()];
                assert_eq!(name.untranslated(), expected);
                prev_offset = offset;
            }
        }
    }

    #[test]
    #[cfg(feature = "micropython")]
    fn test_lookup_qstr_map() {
        for &(qstr, name) in TranslatedString::QSTR_MAP {
            assert!(TranslatedString::from_qstr(qstr) == Some(name));
        }
        // Test a Qstr without translation mapping
        assert!(TranslatedString::from_qstr(Qstr::MP_QSTR_write).is_none());
    }
}

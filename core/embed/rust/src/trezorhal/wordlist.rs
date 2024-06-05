use super::ffi;
use core::{cmp::Ordering, ffi::CStr};

/// Holds all the possible words with the possibility to interact
/// with the "list" - filtering it further, getting their count, etc.
pub struct Wordlist {
    words: &'static [*const cty::c_char],
    /// Holds the length of prefix which was used to filter the list
    /// (how many beginning characters are common for all words).
    prefix_len: usize,
}

impl Wordlist {
    pub fn new(words: &'static [*const cty::c_char], prefix_len: usize) -> Self {
        Self { words, prefix_len }
    }

    /// Initialize BIP39 wordlist.
    pub fn bip39() -> Self {
        Self::new(unsafe { &ffi::BIP39_WORDLIST_ENGLISH }, 0)
    }

    /// Initialize SLIP39 wordlist.
    pub fn slip39() -> Self {
        Self::new(unsafe { &ffi::SLIP39_WORDLIST }, 0)
    }

    /// Returns all possible letters from current wordlist that form a valid
    /// word. Alphabetically sorted.
    pub fn get_available_letters(&self) -> impl Iterator<Item = char> {
        let mut prev_char = '\0';
        let prefix_len = self.prefix_len;
        self.iter().filter_map(move |word| {
            if word.len() <= prefix_len {
                return None;
            }
            let following_char = unwrap!(word.chars().nth(prefix_len));
            if following_char != prev_char {
                prev_char = following_char;
                Some(following_char)
            } else {
                None
            }
        })
    }

    /// Only leaves words that have a specified prefix. Throw away others.
    pub fn filter_prefix(&self, prefix: &str) -> Self {
        // SAFETY: We assume our slice is an array of 0-terminated strings.
        let start = self
            .words
            .partition_point(|&word| matches!(unsafe { prefix_cmp(prefix, word) }, Ordering::Less));
        let end = self.words.partition_point(|&word| {
            !matches!(unsafe { prefix_cmp(prefix, word) }, Ordering::Greater)
        });
        Self::new(&self.words[start..end], prefix.len())
    }

    /// Get a word at the certain position.
    pub fn get(&self, index: usize) -> Option<&'static str> {
        // SAFETY: we assume every word in the wordlist is a valid 0-terminated UTF-8
        // string.
        self.words
            .get(index)
            .map(|word| unsafe { from_utf8_unchecked(*word) })
    }

    /// How many words are currently in the list.
    pub const fn len(&self) -> usize {
        self.words.len()
    }

    /// Iterator of all current words.
    pub fn iter(&self) -> impl Iterator<Item = &'static str> {
        self.words
            .iter()
            .map(|word| unsafe { from_utf8_unchecked(*word) })
    }
}

/// Compare word from wordlist to a prefix.
///
/// The comparison returns Less if the word comes lexicographically before all
/// possible words starting with `prefix`, and Greater if it comes after.
/// Equal is returned if the word starts with `prefix`.
unsafe fn prefix_cmp(prefix: &str, word: *const cty::c_char) -> Ordering {
    // SAFETY: we assume `word` is a pointer to a 0-terminated string.
    for (i, prefix_char) in prefix.as_bytes().iter().enumerate() {
        let word_char = unsafe { *(word.add(i)) } as u8;
        if word_char == 0 {
            // Prefix is longer than word.
            return Ordering::Less;
        } else if *prefix_char != word_char {
            return word_char.cmp(prefix_char);
        }
    }
    Ordering::Equal
}

unsafe fn from_utf8_unchecked<'a>(word: *const cty::c_char) -> &'a str {
    // SAFETY: caller must pass a valid 0-terminated UTF-8 string.
    // This assumption holds for usage on words of the BIP-39/SLIP-39 wordlists.
    unsafe {
        let word = CStr::from_ptr(word as _);
        core::str::from_utf8_unchecked(word.to_bytes())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const BIP39_WORD_COUNT: usize = ffi::BIP39_WORD_COUNT as usize;
    const SLIP39_WORD_COUNT: usize = ffi::SLIP39_WORD_COUNT as usize;

    #[test]
    fn test_filter_prefix_empty() {
        let words = Wordlist::bip39().filter_prefix("");
        assert_eq!(words.len(), BIP39_WORD_COUNT);
        let iter = words.iter();
        assert_eq!(iter.size_hint(), (BIP39_WORD_COUNT, Some(BIP39_WORD_COUNT)));

        let words = Wordlist::slip39().filter_prefix("");
        assert_eq!(words.len(), SLIP39_WORD_COUNT);
        let iter = words.iter();
        assert_eq!(
            iter.size_hint(),
            (SLIP39_WORD_COUNT, Some(SLIP39_WORD_COUNT))
        );
    }

    #[test]
    fn test_filter_prefix() {
        let expected_result = vec!["strategy", "street", "strike", "strong", "struggle"];
        let result = Wordlist::bip39()
            .filter_prefix("str")
            .iter()
            .collect::<Vec<_>>();
        assert_eq!(result, expected_result);
    }

    #[test]
    fn test_filter_prefix_refine() {
        let expected_result = vec!["strategy", "street", "strike", "strong", "struggle"];
        let words = Wordlist::bip39().filter_prefix("st");
        let result_a = words.filter_prefix("str").iter().collect::<Vec<_>>();
        let result_b = Wordlist::bip39()
            .filter_prefix("str")
            .iter()
            .collect::<Vec<_>>();
        assert_eq!(result_a, expected_result);
        assert_eq!(result_b, expected_result);

        let empty = words.filter_prefix("c");
        assert_eq!(empty.len(), 0);
    }

    #[test]
    fn test_wordlist_get() {
        let words = Wordlist::bip39();
        assert_eq!(words.get(0), Some("abandon"));
        assert_eq!(words.get(BIP39_WORD_COUNT - 1), Some("zoo"));
        assert_eq!(words.get(BIP39_WORD_COUNT), None);
        assert_eq!(words.get(BIP39_WORD_COUNT + 1), None);

        let filtered = words.filter_prefix("str");
        assert_eq!(filtered.get(0), Some("strategy"));
        assert_eq!(filtered.get(filtered.len()), None);
    }

    #[test]
    fn test_filter_prefix_just_one() {
        let expected_result = vec!["stick"];
        let result = Wordlist::bip39()
            .filter_prefix("stick")
            .iter()
            .collect::<Vec<_>>();
        assert_eq!(result, expected_result);
    }
    #[test]
    fn test_get_available_letters() {
        let result = Wordlist::bip39()
            .filter_prefix("ab")
            .get_available_letters()
            .collect::<Vec<_>>();
        let expected_result = vec!['a', 'i', 'l', 'o', 's', 'u'];
        assert_eq!(result, expected_result);

        let result = Wordlist::bip39()
            .filter_prefix("str")
            .get_available_letters()
            .collect::<Vec<_>>();
        let expected_result = vec!['a', 'e', 'i', 'o', 'u'];
        assert_eq!(result, expected_result);

        let result = Wordlist::bip39()
            .filter_prefix("zoo")
            .get_available_letters()
            .collect::<Vec<_>>();
        let expected_result = vec![];
        assert_eq!(result, expected_result);

        let result = Wordlist::bip39()
            .get_available_letters()
            .collect::<Vec<_>>();
        let expected_result = vec![
            'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q',
            'r', 's', 't', 'u', 'v', 'w', 'y', 'z',
        ];
        assert_eq!(result, expected_result);
    }
}

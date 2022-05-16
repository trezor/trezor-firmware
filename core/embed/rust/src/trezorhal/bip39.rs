use super::ffi;
use core::cmp::Ordering;
use cstr_core::CStr;

unsafe fn from_utf8_unchecked<'a>(word: *const cty::c_char) -> &'a str {
    // SAFETY: caller must pass a valid 0-terminated UTF-8 string.
    // This assumption holds for usage on words of the BIP-39 wordlist.
    unsafe {
        let word = CStr::from_ptr(word);
        core::str::from_utf8_unchecked(word.to_bytes())
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

pub fn complete_word(prefix: &str) -> Option<&'static str> {
    if prefix.is_empty() {
        None
    } else {
        Wordlist::all().filter_prefix(prefix).iter().next()
    }
}

pub fn word_completion_mask(prefix: &str) -> u32 {
    // SAFETY: `mnemonic_word_completion_mask` shouldn't retain nor modify the
    // passed byte string, making the call safe.
    unsafe { ffi::mnemonic_word_completion_mask(prefix.as_ptr() as _, prefix.len() as _) }
}

/// Returns all possible letters that form a valid word together with some
/// prefix.
pub fn get_available_letters(prefix: &str) -> impl Iterator<Item = char> {
    const CHARS: [char; 26] = [
        'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r',
        's', 't', 'u', 'v', 'w', 'x', 'y', 'z',
    ];

    let mask = word_completion_mask(prefix);
    CHARS
        .iter()
        .filter(move |ch| bitmask_from_char(ch) & mask != 0)
        .copied()
}

fn bitmask_from_char(ch: &char) -> u32 {
    1 << (*ch as u8 - b'a')
}

pub struct Wordlist(&'static [*const cty::c_char]);

impl Wordlist {
    pub fn all() -> Self {
        Self(unsafe { &ffi::BIP39_WORDLIST_ENGLISH })
    }

    pub const fn empty() -> Self {
        Self(&[])
    }

    pub fn filter_prefix(&self, prefix: &str) -> Self {
        let mut start = 0usize;
        let mut end = self.0.len();
        for (i, word) in self.0.iter().enumerate() {
            // SAFETY: We assume our slice is an array of 0-terminated strings.
            match unsafe { prefix_cmp(prefix, *word) } {
                Ordering::Less => {
                    start = i + 1;
                }
                Ordering::Greater => {
                    end = i;
                    break;
                }
                _ => {}
            }
        }
        Self(&self.0[start..end])
    }

    pub fn get(&self, index: usize) -> Option<&'static str> {
        // SAFETY: we assume every word in the wordlist is a valid 0-terminated UTF-8
        // string.
        self.0
            .get(index)
            .map(|word| unsafe { from_utf8_unchecked(*word) })
    }

    pub const fn len(&self) -> usize {
        self.0.len()
    }

    pub fn iter(&self) -> impl Iterator<Item = &'static str> {
        self.0
            .iter()
            .map(|word| unsafe { from_utf8_unchecked(*word) })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use cstr_core::cstr;

    const BIP39_WORD_COUNT: usize = ffi::BIP39_WORD_COUNT as usize;

    #[test]
    fn test_prefix_cmp() {
        assert_eq!(
            unsafe { prefix_cmp("", cstr!("").as_ptr()) },
            Ordering::Equal
        );

        assert_eq!(
            unsafe { prefix_cmp("b", cstr!("").as_ptr()) },
            Ordering::Less
        );
        assert_eq!(
            unsafe { prefix_cmp("b", cstr!("a").as_ptr()) },
            Ordering::Less
        );
        assert_eq!(
            unsafe { prefix_cmp("b", cstr!("b").as_ptr()) },
            Ordering::Equal
        );
        assert_eq!(
            unsafe { prefix_cmp("b", cstr!("below").as_ptr()) },
            Ordering::Equal
        );
        assert_eq!(
            unsafe { prefix_cmp("b", cstr!("c").as_ptr()) },
            Ordering::Greater
        );

        assert_eq!(
            unsafe { prefix_cmp("bartender", cstr!("bar").as_ptr()) },
            Ordering::Less
        );
    }

    #[test]
    fn test_filter_prefix_empty() {
        let words = Wordlist::all().filter_prefix("");
        assert_eq!(words.len(), BIP39_WORD_COUNT);
        let iter = words.iter();
        assert_eq!(iter.size_hint(), (BIP39_WORD_COUNT, Some(BIP39_WORD_COUNT)));
    }

    #[test]
    fn test_filter_prefix() {
        let expected_result = vec!["strategy", "street", "strike", "strong", "struggle"];
        let result = Wordlist::all()
            .filter_prefix("str")
            .iter()
            .collect::<Vec<_>>();
        assert_eq!(result, expected_result);
    }

    #[test]
    fn test_filter_prefix_refine() {
        let expected_result = vec!["strategy", "street", "strike", "strong", "struggle"];
        let words = Wordlist::all().filter_prefix("st");
        let result_a = words.filter_prefix("str").iter().collect::<Vec<_>>();
        let result_b = Wordlist::all()
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
        let words = Wordlist::all();
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
        let result = Wordlist::all()
            .filter_prefix("stick")
            .iter()
            .collect::<Vec<_>>();
        assert_eq!(result, expected_result);
    }

    #[test]
    fn test_word_completion_mask() {
        let result = word_completion_mask("ab");
        assert_eq!(result, 0b101000100100100000001);
        let result = word_completion_mask("zoo");
        assert_eq!(result, 0b0);
    }

    #[test]
    fn test_get_available_letters() {
        let expected_result = vec!['a', 'i', 'l', 'o', 's', 'u'];
        let result = get_available_letters("ab").collect::<Vec<_>>();
        assert_eq!(result, expected_result);

        let expected_result = vec!['a', 'e', 'i', 'o', 'u'];
        let result = get_available_letters("str").collect::<Vec<_>>();
        assert_eq!(result, expected_result);

        let result = get_available_letters("zoo").collect::<Vec<_>>();
        assert_eq!(result.len(), 0);
    }

    #[test]
    fn test_bitmask_from_char() {
        assert_eq!(bitmask_from_char(&'a'), 0b1);
        assert_eq!(bitmask_from_char(&'b'), 0b10);
        assert_eq!(bitmask_from_char(&'c'), 0b100);
        assert_eq!(bitmask_from_char(&'m'), 0b1000000000000);
        assert_eq!(bitmask_from_char(&'z'), 0b10000000000000000000000000);
    }
}

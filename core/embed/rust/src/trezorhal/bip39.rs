use super::{ffi, wordlist::Wordlist};

pub fn complete_word(prefix: &str) -> Option<&'static str> {
    if prefix.is_empty() {
        None
    } else {
        Wordlist::bip39().filter_prefix(prefix).iter().next()
    }
}

pub fn options_num(prefix: &str) -> Option<usize> {
    if prefix.is_empty() {
        None
    } else {
        Some(Wordlist::bip39().filter_prefix(prefix).len())
    }
}

pub fn word_completion_mask(prefix: &str) -> u32 {
    // SAFETY: `mnemonic_word_completion_mask` shouldn't retain nor modify the
    // passed byte string, making the call safe.
    unsafe { ffi::mnemonic_word_completion_mask(prefix.as_ptr() as _, prefix.len() as _) }
}

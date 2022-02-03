use cstr_core::CStr;

extern "C" {
    // trezor-crypto/bip39.h
    fn mnemonic_complete_word(prefix: *const cty::c_char, len: cty::c_int) -> *const cty::c_char;
    fn mnemonic_word_completion_mask(prefix: *const cty::c_char, len: cty::c_int) -> u32;
}

pub fn complete_word(prefix: &str) -> Option<&'static str> {
    if prefix.is_empty() {
        None
    } else {
        // SAFETY: `mnemonic_complete_word` shouldn't retain nor modify the passed byte
        // string, making the call safe.
        let word = unsafe { mnemonic_complete_word(prefix.as_ptr() as _, prefix.len() as _) };
        if word.is_null() {
            None
        } else {
            // SAFETY: On success, `mnemonic_complete_word` should return a 0-terminated
            // UTF-8 string with static lifetime.
            Some(unsafe { CStr::from_ptr(word).to_str().unwrap_unchecked() })
        }
    }
}

pub fn word_completion_mask(prefix: &str) -> u32 {
    // SAFETY: `mnemonic_word_completion_mask` shouldn't retain nor modify the
    // passed byte string, making the call safe.
    unsafe { mnemonic_word_completion_mask(prefix.as_ptr() as _, prefix.len() as _) }
}

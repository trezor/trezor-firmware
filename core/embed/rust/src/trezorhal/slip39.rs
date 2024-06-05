use core::{ffi::CStr, str};

use super::ffi;

/// Calculates which buttons still can be pressed after some already were.
/// Returns a 9-bit bitmask, where each bit specifies which buttons
/// can be further pressed (there are still words in this combination).
/// LSB denotes first button.
///
/// Example: 110000110 - second, third, eighth and ninth button still can be
/// pressed.
pub fn word_completion_mask(prefix: u16) -> Option<u16> {
    if !(1..=9999).contains(&prefix) {
        None
    } else {
        Some(unsafe { ffi::slip39_word_completion_mask(prefix) })
    }
}

/// Finds the first word that fits the given button prefix.
pub fn button_sequence_to_word(prefix: u16) -> Option<&'static str> {
    let word = unsafe { ffi::button_sequence_to_word(prefix) };
    if word.is_null() {
        None
    } else {
        // SAFETY: On success, `button_sequence_to_word` should return a 0-terminated
        // UTF-8 string with static lifetime.
        Some(unsafe { str::from_utf8_unchecked(CStr::from_ptr(word as _).to_bytes()) })
    }
}

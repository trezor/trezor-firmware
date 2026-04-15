//! String access collector for emulator instrumentation.
//!
//! Records every `TR` (TranslatedString) access in an in-memory bitset.
//! Enabled only when the `ui_string_collector` Cargo feature is active.
//!
//! Usage:
//! - `record(tr)` is called from `TString::map()` on every translated string
//!   access (hot path, O(1) bit-set operation).
//! - `get_and_clear()` is called via the `trezortranslate.get_string_log()`
//!   MicroPython function, which is in turn invoked by the DebugLink
//!   `DebugLinkGetStringLog` handler to retrieve (and atomically reset) the
//!   raw bitmap of accessed translation keys.  Name resolution is done on the
//!   host side using `order.json`.

use spin::RwLock;

use super::translated_string::TranslatedString;

pub type WordType = u64;
const BITS_PER_WORD: usize = WordType::BITS as usize;

pub const NWORDS: usize = TranslatedString::COUNT.div_ceil(BITS_PER_WORD);

static STRING_LOG: RwLock<[WordType; NWORDS]> = RwLock::new([0; NWORDS]);

/// Record a single translated-string access.
///
/// This is called from the hot path of `TString::map()`. It must be as cheap
/// as possible: a try-lock followed by a single bit-set if the lock is
/// uncontested.
#[inline]
pub fn record(tr: TranslatedString) {
    let idx = tr as usize;
    let word = idx / BITS_PER_WORD;
    let bit = idx % BITS_PER_WORD;
    // Bounds check (statically should never fail, but avoids UB if order.json
    // grows beyond expectation without updating NWORDS).
    if word < NWORDS {
        STRING_LOG.write()[word] |= (1 as WordType) << bit;
    }
}

/// Return a snapshot of all recorded strings without clearing the log.
pub fn get() -> [WordType; NWORDS] {
    *STRING_LOG.read()
}

/// Return a snapshot of all recorded strings and atomically clear the log.
pub fn get_and_clear() -> [WordType; NWORDS] {
    let mut log = STRING_LOG.write();
    let snapshot = *log;
    *log = [0; NWORDS];
    snapshot
}


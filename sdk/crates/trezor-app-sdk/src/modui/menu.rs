//! Presenting a block's extra data, and its way out.
//!
//! Private. An app lists labelled extras and says whether the block may be
//! abandoned; this turns that into whatever the screen actually offers. Today
//! that is a menu, because the renderer has one — which is exactly why menus
//! are not in the app's vocabulary. The choice can change here without any
//! block signature moving.
//!
//! Core's own UI machinery drives generic menus with callbacks. This is the
//! thin piece that builds one out of what an app is allowed to say.

use super::extra::{Extra, ExtraItem};
use super::{UiOutcome, call_raw};
use crate::structs::{SelectMenu, ShowProperties, StrSlice, TrezorUiEnum, TrezorUiResult};
use crate::{Error, Result};

// ============================================================================
// Constants
// ============================================================================

/// Entries the renderer can show at once, counting the way out.
pub(super) const MAX_ENTRIES: usize = 6;

/// Label of the entry that abandons the block.
const LEAVE: &str = "Cancel";

// ============================================================================
// Entry point
// ============================================================================

/// Shows what a block offers besides its main screen.
///
/// `Some` means the user decided the block from here; `None` means they merely
/// looked, and the main screen should come back.
pub(super) fn open(extras: &[ExtraItem<'_>], cancel: bool) -> Result<Option<UiOutcome>> {
    let count = extras.len() + usize::from(cancel);
    if count == 0 || count > MAX_ENTRIES {
        return Err(Error::ValueError("too many extras for one screen"));
    }

    let mut titles = [StrSlice::default(); MAX_ENTRIES];
    for (slot, extra) in titles.iter_mut().zip(extras) {
        *slot = extra.label.into();
    }
    if cancel {
        titles[extras.len()] = LEAVE.into();
    }

    loop {
        let request = TrezorUiEnum::SelectMenu(SelectMenu::new(&titles[..count], None, 0));

        match call_raw(&request)? {
            TrezorUiResult::Integer(chosen) => {
                let chosen = chosen as usize;
                match extras.get(chosen) {
                    Some(extra) => show(extra)?,
                    // Past the extras lies the way out, which exists only when
                    // the block asked for one.
                    None if cancel && chosen == extras.len() => {
                        return Ok(Some(UiOutcome::Cancelled));
                    }
                    None => return Err(Error::InvalidMessage),
                }
            }
            // Closed without choosing: back to the main screen.
            TrezorUiResult::Confirmed | TrezorUiResult::Cancelled => return Ok(None),
            _ => return Err(Error::InvalidMessage),
        }
    }
}

// ============================================================================
// Internals
// ============================================================================

/// Shows one extra. Dismissing it comes back here, so it carries no decision.
fn show(extra: &ExtraItem<'_>) -> Result<()> {
    match extra.value {
        Extra::Simple(props) => {
            let request = ShowProperties::new(extra.label, props, None, None, 0);
            call_raw(&TrezorUiEnum::ShowProperties(request))?;
        }
        // Paging is unsolved; this is where the fetch loop belongs once its
        // shape is settled. Refusing is wrong, but it is honestly wrong rather
        // than quietly wrong.
        Extra::Paginated(_) => return Err(Error::ValueError("paginated extras not implemented")),
    }

    Ok(())
}

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

use super::BR_CODE_OTHER;
use super::extra::{Extra, ExtraItem};
use super::screen::{Screen, call_once};
use crate::alloc_types::String;
use crate::structs::{SelectMenu, ShowProperties, StrSlice, TrezorUiEnum, UiReply};
use crate::{Error, Result};

// ============================================================================
// Constants
// ============================================================================

/// Entries the renderer can show at once, counting the way out.
pub(super) const MAX_ENTRIES: usize = 6;

/// Appended to the block's step name for the list of extras.
const STEP_MENU: &str = "/menu";

/// Appended to the block's step name for one extra's own screen.
const STEP_DETAILS: &str = "/details";

// ============================================================================
// Entry point
// ============================================================================

/// Checks that a block's extras can be offered, before anything is shown.
///
/// Every block calls this first, so a list that cannot be shown fails as the
/// block is called, not later, when the person opens the menu mid-flow.
pub(super) fn check_extras(extras: &[ExtraItem<'_>], cancel: bool) -> Result<()> {
    if extras.len() + usize::from(cancel) > MAX_ENTRIES {
        return Err(Error::ValueError("too many extras for one screen"));
    }
    if extras
        .iter()
        .any(|extra| matches!(extra.value, Extra::Chunked(_)))
    {
        return Err(Error::ValueError("chunked extras not implemented"));
    }
    Ok(())
}

/// Shows what a block offers besides its main screen.
///
/// `Some` means the person decided the block from here; `None` means they merely
/// looked, and the main screen should come back.
pub(super) fn open(
    extras: &[ExtraItem<'_>],
    cancel: bool,
    br: Option<&str>,
) -> Result<Option<UiReply>> {
    // `check_extras` has already refused a list that cannot be shown, so an empty one
    // here means core answered "show more" for a screen that offered nothing.
    let count = extras.len() + usize::from(cancel);
    if count == 0 {
        return Err(Error::InvalidMessage);
    }

    let mut titles = [StrSlice::default(); MAX_ENTRIES];
    for (slot, extra) in titles.iter_mut().zip(extras) {
        *slot = extra.label.into();
    }
    if cancel {
        // Another word this library should not be choosing; see the note
        // in `confirm_data`. The way out is an ordinary entry because the
        // renderer ignores `SelectMenu`'s own `cancel` field.
        titles[extras.len()] = "Cancel".into();
    }

    // These screens exist only because a block offered extras, so their names
    // hang off the block's. The app never writes them: it names its step, and
    // the library says which part of that step the person is looking at. A block
    // that announces nothing passes that silence down rather than naming a
    // step of nothing.
    let menu_step = br.map(|br| step(br, STEP_MENU));
    let details_step = br.map(|br| step(br, STEP_DETAILS));

    let request = TrezorUiEnum::SelectMenu(SelectMenu::new(
        &titles[..count],
        None,
        menu_step.as_deref(),
        BR_CODE_OTHER,
    ));
    let screen = Screen::new();
    let mut first = true;

    loop {
        // Looking at an extra and coming back should land on the entry that
        // was chosen, not at the top of the list, so the menu is reopened.
        let reply = if first {
            first = false;
            screen.show(&request)?
        } else {
            screen.reshow(&request)?
        };

        match reply {
            UiReply::Choice(chosen) => {
                let chosen = chosen as usize;
                match extras.get(chosen) {
                    Some(extra) => show(extra, details_step.as_deref())?,
                    // Past the extras lies the way out, which exists only when
                    // the block asked for one.
                    None if cancel && chosen == extras.len() => {
                        return Ok(Some(UiReply::Cancelled));
                    }
                    None => return Err(Error::InvalidMessage),
                }
            }
            // Closed without choosing: back to the main screen.
            UiReply::Confirmed | UiReply::Cancelled => return Ok(None),
            _ => return Err(Error::InvalidMessage),
        }
    }
}

// ============================================================================
// Internals
// ============================================================================

/// The block's step name with a suffix naming which part of it this is.
fn step(br: &str, suffix: &str) -> String {
    let mut name = String::with_capacity(br.len() + suffix.len());
    name.push_str(br);
    name.push_str(suffix);
    name
}

/// Shows one extra. Dismissing it comes back here, so it carries no decision.
fn show(extra: &ExtraItem<'_>, br: Option<&str>) -> Result<()> {
    match extra.value {
        Extra::Simple(props) => {
            let request = ShowProperties::new(extra.label, props, None, br, BR_CODE_OTHER);
            call_once(&TrezorUiEnum::ShowProperties(request))?;
        }
        // Fetching chunk by chunk is unsolved; this is where that loop belongs
        // once its shape is settled. `check_extras` refuses these before anything is
        // shown, so this arm is only reached if that check is bypassed.
        Extra::Chunked(_) => return Err(Error::ValueError("chunked extras not implemented")),
    }

    Ok(())
}

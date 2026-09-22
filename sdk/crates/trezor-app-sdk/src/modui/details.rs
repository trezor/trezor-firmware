//! The details menu a block can carry.
//!
//! Some blocks show a main screen plus a menu holding extra facts. Opening the
//! menu, reading a page and coming back is navigation *inside* one block: the
//! caller makes one blocking call, gets one outcome, and never learns whether
//! the menu was opened at all.
//!
//! Scaffolding: the walk runs here today, driving `SelectMenu`/`ShowProperties`
//! over IPC one screen at a time. It belongs in the Python UI driver, which is
//! where menu walking is meant to live.
//!
//! # Example
//!
//! ```text
//! // A block delegates its main screen and menu to this helper:
//! details::confirm(params.details, || {
//!     call_raw(&TrezorUiEnum::ConfirmValue(request()))
//! })
//!
//! // `details` is the block's own `Option<(title, props)>` parameter.
//! ```

use super::{UiOutcome, call_raw};
use crate::structs::{
    ConfirmAction, Property, SelectMenu, ShowProperties, StrSlice, TrezorUiEnum, TrezorUiResult,
};
use crate::{Error, Result};

// ============================================================================
// Constants
// ============================================================================

/// Label of the entry that abandons the block. Fixed by the library, like every
/// other piece of chrome.
const CANCEL: &str = "Cancel";

// ============================================================================
// Data types
// ============================================================================

/// An extra page of facts a block can offer: its title and what it lists.
///
/// A plain pair rather than a named type — it is only ever a block's optional
/// `details` parameter, and a struct for it would be one more thing to import.
pub(super) type Details<'a> = (&'a str, &'a [Property<'a>]);

// ============================================================================
// Entry point
// ============================================================================

/// Runs a block's main screen, servicing its menu until the user decides.
pub(super) fn confirm<F>(details: Option<Details<'_>>, mut main: F) -> Result<UiOutcome>
where
    F: FnMut() -> Result<TrezorUiResult>,
{
    loop {
        let result = main()?;

        match result {
            TrezorUiResult::Confirmed => return Ok(UiOutcome::Confirmed),
            TrezorUiResult::Cancelled => return Ok(UiOutcome::Cancelled),
            // The user opened the menu. Leaving it lands back on the main screen
            // unless they chose to abandon the block.
            TrezorUiResult::Info => {
                if let Some(outcome) = walk(details)? {
                    return Ok(outcome);
                }
            }
            TrezorUiResult::Back | TrezorUiResult::Integer(_) => {
                return Err(Error::InvalidMessage);
            }
        }
    }
}

// ============================================================================
// Internals
// ============================================================================

/// Shows the menu. `None` means the user left it and wants the main screen back.
fn walk(details: Option<Details<'_>>) -> Result<Option<UiOutcome>> {
    // At most one entry today; the wire carries a list regardless.
    let entry: [StrSlice; 1] = [details.map_or("", |(title, _)| title).into()];
    let entries = if details.is_some() {
        &entry[..]
    } else {
        &entry[..0]
    };

    loop {
        let request = SelectMenu::new(entries, Some(CANCEL), 0);

        match call_raw(&TrezorUiEnum::SelectMenu(request))? {
            TrezorUiResult::Integer(0) => {
                if let Some(details) = details {
                    show(details)?;
                }
            }
            // The menu was closed without choosing anything.
            TrezorUiResult::Confirmed => return Ok(None),
            // The cancel entry: abandoning the block needs confirming.
            TrezorUiResult::Cancelled => {
                if confirm_cancel()? {
                    return Ok(Some(UiOutcome::Cancelled));
                }
            }
            _ => return Err(Error::InvalidMessage),
        }
    }
}

/// Shows one details page. Dismissing it returns to the menu, so the result of
/// the screen carries no decision and is discarded.
fn show((title, props): Details<'_>) -> Result<()> {
    let request = ShowProperties::new(title, props, None, None, 0);
    call_raw(&TrezorUiEnum::ShowProperties(request))?;
    Ok(())
}

/// Asks whether to abandon the block. `true` means leave it.
fn confirm_cancel() -> Result<bool> {
    let request = ConfirmAction::new(CANCEL, "", None, None, false, None, true, None, 0, false);

    match call_raw(&TrezorUiEnum::ConfirmAction(request))? {
        TrezorUiResult::Confirmed => Ok(true),
        TrezorUiResult::Cancelled => Ok(false),
        _ => Err(Error::InvalidMessage),
    }
}

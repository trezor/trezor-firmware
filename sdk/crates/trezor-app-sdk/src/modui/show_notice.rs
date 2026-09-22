//! Telling the user something, at one of three levels of alarm.
//!
//! One block replaces what used to be three (`show_danger`, `show_warning`,
//! `show_info_with_cancel`). The app picks the severity — it always could, by
//! picking which function to call — but what a severity *looks like* and what
//! gesture it demands follow from it, and are not the app's to choose.
//!
//! # Example
//!
//! ```no_run
//! use trezor_app_sdk::modui::{self as ui, Severity, ShowNotice};
//!
//! fn warn_unknown_contract() -> trezor_app_sdk::Result<()> {
//!     ui::show_notice(ShowNotice::new(
//!         Severity::Danger,
//!         "Important",
//!         "Unknown contract address.",
//!         &[],
//!         false,
//!     ))?
//!     .confirmed()
//! }
//! ```

use super::extra::ExtraItem;
use super::{UiOutcome, call};
use crate::structs::{ShowDanger, TrezorUiEnum};
use crate::{Error, Result};

// ============================================================================
// Data types
// ============================================================================

/// How much alarm a notice carries.
#[derive(Copy, Clone, PartialEq, Eq)]
pub enum Severity {
    /// Worth reading; dismissible.
    Info,
    /// Worth pausing over.
    Warning,
    /// Must be acknowledged deliberately; never auto-dismisses.
    Danger,
}

/// Parameters for [`show_notice`].
pub struct ShowNotice<'a> {
    severity: Severity,
    title: &'a str,
    content: &'a str,
    extras: &'a [ExtraItem<'a>],
    cancel: bool,
}

impl<'a> ShowNotice<'a> {
    /// A notice of the given severity.
    pub fn new(
        severity: Severity,
        title: &'a str,
        content: &'a str,
        extras: &'a [ExtraItem<'a>],
        cancel: bool,
    ) -> Self {
        Self {
            severity,
            title,
            content,
            extras,
            cancel,
        }
    }

    /// Whether the screen has anything to offer besides its main content.
    fn offers_more(&self) -> bool {
        !self.extras.is_empty() || self.cancel
    }
}

// ============================================================================
// Entry point
// ============================================================================

/// Shows a notice and waits for the user to act on it.
///
/// Scaffolding note: every severity currently renders through the old
/// `ShowDanger` variant, the only one of the three whose wire shape carries
/// what this block needs. Severity is therefore not yet visible to the
/// renderer — the first thing to fix when the wire is rewritten.
pub fn show_notice(params: ShowNotice<'_>) -> Result<UiOutcome> {
    // This block's wire has no menu button yet, so anything behind one would
    // be silently unreachable. Refusing is worse to use and better to debug.
    if !params.extras.is_empty() {
        return Err(Error::ValueError("extras not yet supported by this block"));
    }
    let _ = params.severity;

    let request = ShowDanger::new(
        params.title,
        params.content,
        None, // ButtonRequest: emitted on the trusted side, not from here
        0,
        None, // verb_cancel: chrome, follows the severity
        None, // menu_title: the library decides how extras are shown
    );

    call(
        &TrezorUiEnum::ShowDanger(request),
        params.extras,
        params.cancel,
    )
}

//! The generic yes/no block.
//!
//! # Example
//!
//! ```no_run
//! use trezor_app_sdk::modui::{self as ui, ConfirmAction};
//!
//! fn confirm_delete() -> trezor_app_sdk::Result<()> {
//!     ui::confirm_action(ConfirmAction::new(
//!         "Delete",
//!         "Are you sure?",
//!         Some("This cannot be undone."),
//!         None,
//!         None,
//!     ))?
//!     .confirmed()
//! }
//! ```

use super::details::{self, Details};
use super::{UiOutcome, call_raw};
use crate::Result;
use crate::structs::{ConfirmAction as WireConfirmAction, Property, TrezorUiEnum};

// ============================================================================
// Data types
// ============================================================================

/// Parameters for [`confirm_action`].
///
/// `title` and `action` are the facts being confirmed and are the app's to
/// choose. The trust signals are not here at all: the confirm gesture and its
/// label, whether the screen offers back-navigation, and the ButtonRequest
/// identity are fixed by the block.
pub struct ConfirmAction<'a> {
    title: &'a str,
    action: &'a str,
    description: Option<&'a str>,
    subtitle: Option<&'a str>,
    details: Option<Details<'a>>,
}

impl<'a> ConfirmAction<'a> {
    /// A confirmation screen headed `title`, asking the user about `action`.
    ///
    /// `details` is an extra page of facts, titled and listed, reachable from
    /// the block's menu.
    pub fn new(
        title: &'a str,
        action: &'a str,
        description: Option<&'a str>,
        subtitle: Option<&'a str>,
        details: Option<(&'a str, &'a [Property<'a>])>,
    ) -> Self {
        Self {
            title,
            action,
            description,
            subtitle,
            details,
        }
    }
}

// ============================================================================
// Entry point
// ============================================================================

/// Shows a generic confirmation screen and waits for the user to answer.
pub fn confirm_action(params: ConfirmAction<'_>) -> Result<UiOutcome> {
    let has_menu = params.details.is_some();

    details::confirm(params.details, || {
        let request = WireConfirmAction::new(
            params.title,
            params.action,
            params.description,
            params.subtitle,
            false, // hold: derived from the block, not the app
            None,  // verb: the label follows the gesture
            true,  // cancel: the user can always leave
            None,  // ButtonRequest: emitted on the trusted side, not from here
            0,
            has_menu, // external_menu: how the details menu is reached
        );

        call_raw(&TrezorUiEnum::ConfirmAction(request))
    })
}

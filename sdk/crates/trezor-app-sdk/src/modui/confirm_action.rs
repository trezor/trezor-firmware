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
//!         &[],
//!         true,
//!     ))?
//!     .confirmed()
//! }
//! ```
//!
//! A screen can carry more than the thing it confirms. The app lists what it
//! has, labelled; how any of it is presented — a menu, extra pages, something
//! else later — is the library's business and deliberately not sayable here.
//!
//! ```no_run
//! use trezor_app_sdk::modui::{self as ui, ConfirmAction, ExtraItem, Property};
//!
//! fn sign_with_extras(account: &str, path: &str) -> trezor_app_sdk::Result<()> {
//!     let account_facts = [
//!         Property::plain("Account", account),
//!         Property::plain("Derivation path", path),
//!     ];
//!     let fee_facts = [Property::plain("Fee limit", "10 TRX")];
//!
//!     let extras = [
//!         ExtraItem::simple("Account info", &account_facts),
//!         ExtraItem::simple("Fee details", &fee_facts),
//!     ];
//!
//!     ui::confirm_action(ConfirmAction::new(
//!         "Send",
//!         "Sign the transaction?",
//!         None,
//!         None,
//!         &extras,
//!         true, // the signing can be abandoned from here
//!     ))?
//!     .confirmed()
//! }
//! ```

use super::extra::ExtraItem;
use super::{UiOutcome, call};
use crate::Result;
use crate::structs::{ConfirmAction as WireConfirmAction, TrezorUiEnum};

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
    extras: &'a [ExtraItem<'a>],
    cancel: bool,
}

impl<'a> ConfirmAction<'a> {
    /// A confirmation screen headed `title`, asking the user about `action`.
    ///
    /// `extras` are labelled pieces the screen can also offer; `cancel` says
    /// whether the block may be abandoned from there. How either is presented
    /// is the library's choice, not the caller's.
    pub fn new(
        title: &'a str,
        action: &'a str,
        description: Option<&'a str>,
        subtitle: Option<&'a str>,
        extras: &'a [ExtraItem<'a>],
        cancel: bool,
    ) -> Self {
        Self {
            title,
            action,
            description,
            subtitle,
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

/// Shows a generic confirmation screen and waits for the user to answer.
pub fn confirm_action(params: ConfirmAction<'_>) -> Result<UiOutcome> {
    let request = TrezorUiEnum::ConfirmAction(WireConfirmAction::new(
        params.title,
        params.action,
        params.description,
        params.subtitle,
        false, // hold: derived from the block, not the app
        None,  // verb: the label follows the gesture
        true,  // cancel: the user can always leave
        None,  // ButtonRequest: emitted on the trusted side, not from here
        0,
        params.offers_more(), // external_menu: how the menu is reached
    ));

    call(&request, params.extras, params.cancel)
}

//! The generic yes/no block. The public docs live on [`action`].
//!
//! WIP: manual test results with extras (testapp), bolt (T2T1): no menu, so
//! the extras cannot be reached.

use crate::Result;
use crate::modui::internal::{BR_CODE_OTHER, call};
use crate::modui::{Commitment, ExtraItem, UiReply};
use crate::traits::ui::ConfirmAction as WireConfirmAction;

// ============================================================================
// Data types
// ============================================================================

/// Parameters for [`action`], built by [`Action::new`].
///
/// Only what the screen says is here. The confirm gesture and its label are
/// fixed by the block and are not the app's to choose.
pub struct Action<'a> {
    title: &'a str,
    action: &'a str,
    description: Option<&'a str>,
    subtitle: Option<&'a str>,
    commitment: Commitment,
    br: &'a str,
    extras: &'a [ExtraItem<'a>],
}

impl<'a> Action<'a> {
    /// A confirmation screen headed `title`, asking the person about `action`.
    ///
    /// - `title` — the screen's heading, such as `"Send"`.
    /// - `action` — what the person is being asked to confirm.
    /// - `description` — optional text below the action.
    /// - `subtitle` — optional line under the heading.
    /// - `commitment` — whether confirming this is the person's final yes; see
    ///   [`Commitment`].
    /// - `br` — the step name the host sees; see
    ///   [step names](crate::modui#step-names).
    /// - `extras` — more the person can look at from this screen; see
    ///   [extras](crate::modui#extras-and-the-way-out).
    pub fn new(
        title: &'a str,
        action: &'a str,
        description: Option<&'a str>,
        subtitle: Option<&'a str>,
        commitment: Commitment,
        br: &'a str,
        extras: &'a [ExtraItem<'a>],
    ) -> Self {
        Self {
            title,
            action,
            description,
            subtitle,
            commitment,
            br,
            extras,
        }
    }
}

// ============================================================================
// Entry point
// ============================================================================

/// Asks the person to confirm an action, and waits for the answer.
///
/// The person can always refuse, so the block takes no `cancel`: the way out
/// is on the screen, or in its menu where the menu button takes its place.
///
/// # Errors
///
/// See [errors](crate::modui#errors).
///
/// # Example
///
/// ```no_run
/// use trezor_app_sdk::modui::{Commitment, ExtraItem, Property, confirm};
///
/// fn confirm_sign(account: &str, path: &str) -> trezor_app_sdk::Result<()> {
///     let account_facts = [
///         Property::plain("Account", account),
///         Property::plain("Derivation path", path),
///     ];
///     let extras = [ExtraItem::simple("Account info", &account_facts)];
///
///     confirm::action(confirm::Action::new(
///         "Send",
///         "Sign the transaction?",
///         None,
///         None,
///         Commitment::Step,
///         "app/sign",
///         &extras,
///     ))?
///     .confirmed()
/// }
/// ```
pub fn action(params: Action<'_>) -> Result<UiReply> {
    let request = WireConfirmAction::new(
        params.title,
        params.action,
        params.description,
        params.subtitle,
        params.commitment == Commitment::Final, // hold: follows from the commitment
        None,                                   // verb: the label follows the gesture
        true,                                   // cancel: the person can always leave
        Some(params.br), // br_name: the step's name; the app owns it (see the field docs)
        BR_CODE_OTHER,   // legacy field; see the constant
        !params.extras.is_empty(), // external_menu: how the menu is reached
    );

    // Always refusable: where the menu button takes the screen's own way out,
    // the menu carries it instead.
    call(&request, params.extras, false, true, Some(params.br))
}

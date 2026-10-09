//! The generic yes/no block. The public docs live on [`action`].
//!
//! WIP: bolt has no menu, so the extras cannot be reached.

use crate::app_runtime2::get_ui_or_die;
use crate::modui::internal::answer;
use crate::modui::{Commitment, ExtraItem};
use crate::structs::ConfirmAction;
use crate::traits::ui::UiV1Dyn as _;
use crate::{IntoAppResult, Result};

// ============================================================================
// Data types
// ============================================================================

/// Parameters for [`action`], built by [`Action::new`]: the request core reads,
/// passed through the FFI as is.
///
/// Only what the screen says is here. The confirm gesture and its label are
/// fixed by the block and are not the app's to choose.
pub type Action<'a> = ConfirmAction<'a>;

impl<'a> ConfirmAction<'a> {
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
            title: title.into(),
            action: action.into(),
            description: description.into(),
            subtitle: subtitle.into(),
            commitment,
            br_name: br.into(),
            extras: extras.into(),
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
///     ))
/// }
/// ```
pub fn action(params: Action<'_>) -> Result<()> {
    answer(get_ui_or_die().confirm_action(params).into_app_result()?)
}

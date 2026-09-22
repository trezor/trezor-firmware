//! The generic yes/no block. The public docs live on [`confirm_action`].

use super::extra::ExtraItem;
use super::{BR_CODE_OTHER, UiOutcome, call};
use crate::Result;
use crate::structs::{ConfirmAction as WireConfirmAction, TrezorUiEnum};

// ============================================================================
// Data types
// ============================================================================

/// Parameters for [`confirm_action`], built by [`ConfirmAction::new`].
///
/// Only what the screen says is here. The confirm gesture and its label are
/// fixed by the block and are not the app's to choose.
pub struct ConfirmAction<'a> {
    title: &'a str,
    action: &'a str,
    description: Option<&'a str>,
    subtitle: Option<&'a str>,
    br: &'a str,
    extras: &'a [ExtraItem<'a>],
    cancel: bool,
}

impl<'a> ConfirmAction<'a> {
    /// A confirmation screen headed `title`, asking the person about `action`.
    ///
    /// - `title` — the screen's heading, such as `"Send"`.
    /// - `action` — what the person is being asked to confirm.
    /// - `description` — optional text below the action.
    /// - `subtitle` — optional line under the heading.
    /// - `br` — the step name the host sees; see
    ///   [step names](crate::modui#step-names).
    /// - `extras` — more the person can look at from this screen; see
    ///   [extras](crate::modui#extras-and-the-way-out).
    /// - `cancel` — whether the extras also offer a way to abandon the block.
    pub fn new(
        title: &'a str,
        action: &'a str,
        description: Option<&'a str>,
        subtitle: Option<&'a str>,
        br: &'a str,
        extras: &'a [ExtraItem<'a>],
        cancel: bool,
    ) -> Self {
        Self {
            title,
            action,
            description,
            subtitle,
            br,
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

/// Asks the person to confirm an action, and waits for the answer.
///
/// The person can always refuse from this screen, whatever `cancel` says.
///
/// # Errors
///
/// See [errors](crate::modui#errors).
///
/// # Example
///
/// ```no_run
/// use trezor_app_sdk::modui::{self as ui, ConfirmAction, ExtraItem, Property};
///
/// fn confirm_sign(account: &str, path: &str) -> trezor_app_sdk::Result<()> {
///     let account_facts = [
///         Property::plain("Account", account),
///         Property::plain("Derivation path", path),
///     ];
///     let extras = [ExtraItem::simple("Account info", &account_facts)];
///
///     ui::confirm_action(ConfirmAction::new(
///         "Send",
///         "Sign the transaction?",
///         None,
///         None,
///         "app/sign",
///         &extras,
///         true, // the signing can also be abandoned from the extras
///     ))?
///     .confirmed()
/// }
/// ```
pub fn confirm_action(params: ConfirmAction<'_>) -> Result<UiOutcome> {
    let request = TrezorUiEnum::ConfirmAction(WireConfirmAction::new(
        params.title,
        params.action,
        params.description,
        params.subtitle,
        false,                // hold: derived from the block, not the app
        None,                 // verb: the label follows the gesture
        true,                 // cancel: the person can always leave
        Some(params.br),      // br_name: the step's name; the app owns it (see the field docs)
        BR_CODE_OTHER,        // legacy field; see the constant
        params.offers_more(), // external_menu: how the menu is reached
    ));

    call(&request, params.extras, params.cancel, Some(params.br))
}

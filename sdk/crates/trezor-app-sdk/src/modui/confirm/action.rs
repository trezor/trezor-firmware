//! The generic yes/no layout. The public docs live on [`action`].

use crate::app_runtime2::{get_ui_or_die, system_exit_fatal};
use crate::modui::{Commitment, ExtraItem};
use crate::structs::{ConfirmAction, TrezorUiEnum, TrezorUiResult};
use crate::traits::ui::UiV1Dyn as _;
use crate::{Error, Result};

/// Asks the person to confirm an action, and waits for the answer.
///
/// - `title` — the screen's heading, such as `"Send"`.
/// - `action` — what the person is being asked to confirm.
/// - `subtitle` — optional line under the heading.
/// - `description` — optional text below the action.
/// - `commitment` — whether confirming this is the person's final yes; see
///   [`Commitment`].
/// - `br` — the step name the host sees; see
///   [step names](crate::modui#step-names).
/// - `extras` — more the person can look at from this screen; see
///   [extras](crate::modui#extras-and-the-way-out).
///
/// Only what the screen says is the app's. The confirm gesture and its label
/// are fixed by the layout. The person can always refuse, so the layout takes no
/// `cancel`: the way out is on the screen, or in its menu where the menu
/// button takes its place.
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
///     confirm::action(
///         "Send",
///         "Sign the transaction?",
///         None,
///         None,
///         Commitment::Step,
///         "app/sign",
///         &extras,
///     )
/// }
/// ```
pub fn action(
    title: &str,
    action: &str,
    subtitle: Option<&str>,
    description: Option<&str>,
    commitment: Commitment,
    br: &str,
    extras: &[ExtraItem<'_>],
) -> Result<()> {
    let request = ConfirmAction {
        title: title.into(),
        action: action.into(),
        subtitle: subtitle.into(),
        description: description.into(),
        commitment,
        br_name: br.into(),
        extras: extras.into(),
    };
    match get_ui_or_die()
        .ui_call(TrezorUiEnum::ConfirmAction(request))
        .into_result()
    {
        Ok(TrezorUiResult::Confirmed) => Ok(()),
        Ok(TrezorUiResult::Cancelled) => Err(Error::Cancelled),
        Ok(_) => system_exit_fatal("unexpected UI reply", file!(), line!()),
        Err(e) => system_exit_fatal(e.message(), file!(), line!()),
    }
}

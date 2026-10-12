//! The closing screen of a transaction. The public docs live on
//! [`summary`].

use crate::app_runtime2::{get_ui_or_die, system_exit_fatal};
use crate::modui::ExtraItem;
use crate::structs::{ConfirmSummary, TrezorUiEnum, TrezorUiResult};
use crate::traits::ui::UiV1Dyn as _;
use crate::{Error, Result};

/// Shows the closing summary of a transaction, and waits for the answer.
///
/// - `title` — the screen's heading, such as `"Send"`.
/// - `amount` — optional label and value of what is being sent.
/// - `fee` — optional label and value of what it costs.
/// - `br` — the step name the host sees; see
///   [step names](crate::modui#step-names).
/// - `extras` — more the person can look at from this screen; see
///   [extras](crate::modui#extras-and-the-way-out).
///   The paying account belongs here, like anything else worth listing.
///
/// Usually the last screen before signing: `Ok` is the person's yes to
/// the whole transaction. The person can always refuse it, so the block takes
/// no `cancel`.
///
/// # Errors
///
/// See [errors](crate::modui#errors).
///
/// # Example
///
/// ```no_run
/// use trezor_app_sdk::modui::{ExtraItem, Property, confirm};
///
/// fn confirm_total(amount: &str, fee: &str, account: &str) -> trezor_app_sdk::Result<()> {
///     let account_facts = [Property::plain("Account", account)];
///     let extras = [ExtraItem::simple("Account info", &account_facts)];
///
///     confirm::summary(
///         "Send",
///         Some(("Amount", amount)),
///         Some(("Fee limit", fee)),
///         "app/summary",
///         &extras,
///     )
/// }
/// ```
pub fn summary(
    title: &str,
    amount: Option<(&str, &str)>,
    fee: Option<(&str, &str)>,
    br: &str,
    extras: &[ExtraItem<'_>],
) -> Result<()> {
    let request = ConfirmSummary {
        title: title.into(),
        amount: amount.map(|(_, value)| value).into(),
        amount_label: amount.map(|(label, _)| label).into(),
        fee: fee.map(|(_, value)| value).into(),
        fee_label: fee.map(|(label, _)| label).into(),
        br_name: br.into(),
        extras: extras.into(),
    };
    match get_ui_or_die()
        .ui_call(TrezorUiEnum::ConfirmSummary(request))
        .into_result()
    {
        Ok(TrezorUiResult::Confirmed) => Ok(()),
        Ok(TrezorUiResult::Cancelled) => Err(Error::Cancelled),
        Ok(_) => system_exit_fatal("unexpected UI reply", file!(), line!()),
        Err(e) => system_exit_fatal(e.message(), file!(), line!()),
    }
}

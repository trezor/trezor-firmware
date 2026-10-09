//! The closing screen of a transaction. The public docs live on
//! [`summary`].
//!
//! WIP: bolt has no menu and delizia ignores it, so the extras cannot be
//! reached there.

use crate::Result;
use crate::modui::ExtraItem;
use crate::modui::internal::{answer, call};
use crate::structs::ConfirmSummary;

// ============================================================================
// Data types
// ============================================================================

/// Parameters for [`summary`], built by [`Summary::new`].
pub struct Summary<'a> {
    /// The request as core reads it; it goes through the FFI as is.
    request: ConfirmSummary<'a>,
    /// Shown by the library from the screen's menu; never sent.
    extras: &'a [ExtraItem<'a>],
}

impl<'a> Summary<'a> {
    /// A summary headed `title`.
    ///
    /// - `title` — the screen's heading, such as `"Send"`.
    /// - `amount` — optional label and value of what is being sent.
    /// - `fee` — optional label and value of what it costs.
    /// - `br` — the step name the host sees; see
    ///   [step names](crate::modui#step-names).
    /// - `extras` — more the person can look at from this screen; see
    ///   [extras](crate::modui#extras-and-the-way-out).
    ///   The paying account belongs here, like anything else worth listing.
    pub fn new(
        title: &'a str,
        amount: Option<(&'a str, &'a str)>,
        fee: Option<(&'a str, &'a str)>,
        br: &'a str,
        extras: &'a [ExtraItem<'a>],
    ) -> Self {
        Self {
            request: ConfirmSummary {
                title: title.into(),
                amount: amount.map(|(_, value)| value).into(),
                amount_label: amount.map(|(label, _)| label).into(),
                fee: fee.map_or("", |(_, value)| value).into(),
                fee_label: fee.map_or("", |(label, _)| label).into(),
                br_name: br.into(),
                external_menu: !extras.is_empty(),
            },
            extras,
        }
    }
}

// ============================================================================
// Entry point
// ============================================================================

/// Shows the closing summary of a transaction, and waits for the answer.
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
///     confirm::summary(confirm::Summary::new(
///         "Send",
///         Some(("Amount", amount)),
///         Some(("Fee limit", fee)),
///         "app/summary",
///         &extras,
///     ))
/// }
/// ```
pub fn summary(params: Summary<'_>) -> Result<()> {
    let br = params.request.br_name.as_str();
    answer(call(&params.request, params.extras, Some(br))?)
}

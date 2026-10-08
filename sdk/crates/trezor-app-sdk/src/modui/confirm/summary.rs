//! The closing screen of a transaction. The public docs live on
//! [`summary`].
//!
//! WIP: manual test results (by hand):
//! - caesar (T3B1): with extras the menu, the extras and its way out all
//!   work; without extras there is no menu, as intended. The reference for
//!   what the other blocks should do there.
//! - bolt (T2T1): no menu, so the extras cannot be reached.

use crate::Result;
use crate::modui::ExtraItem;
use crate::modui::internal::{BR_CODE_OTHER, answer, call};
use crate::traits::ui::ConfirmSummary as WireConfirmSummary;

// ============================================================================
// Data types
// ============================================================================

/// Parameters for [`summary`], built by [`Summary::new`].
pub struct Summary<'a> {
    title: &'a str,
    amount: Option<(&'a str, &'a str)>,
    fee: Option<(&'a str, &'a str)>,
    br: &'a str,
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
            title,
            amount,
            fee,
            br,
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
    let request = WireConfirmSummary::new(
        params.title,
        params.amount.map(|(_, value)| value),
        params.amount.map(|(label, _)| label),
        params.fee.map_or("", |(_, value)| value),
        params.fee.map_or("", |(label, _)| label),
        // The wire's labelled slots are the renderer's own hardcoded menu.
        // The extras go through the same menu every other block uses instead,
        // so how many fit is the shared limit rather than this screen's
        // accident.
        None,
        None,
        None,
        None,
        false,                     // back_button: sequences run forward only
        !params.extras.is_empty(), // external_menu: how the extras are reached
        Some(params.br),           // br_name: the step's name; the app owns it
        BR_CODE_OTHER,             // legacy field; see the constant
    );

    answer(call(&request, params.extras, Some(params.br))?)
}

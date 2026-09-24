//! The closing screen of a transaction. The public docs live on
//! [`confirm_summary`].

use super::extra::ExtraItem;
use super::{BR_CODE_OTHER, UiReply, call};
use crate::Result;
use crate::structs::{ConfirmSummary as WireConfirmSummary, TrezorUiEnum};

// ============================================================================
// Data types
// ============================================================================

/// Parameters for [`confirm_summary`], built by [`ConfirmSummary::new`].
pub struct ConfirmSummary<'a> {
    title: &'a str,
    amount: Option<(&'a str, &'a str)>,
    fee: Option<(&'a str, &'a str)>,
    br: &'a str,
    extras: &'a [ExtraItem<'a>],
}

impl<'a> ConfirmSummary<'a> {
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

    /// Whether the screen has anything to offer besides its main content.
    fn offers_more(&self) -> bool {
        !self.extras.is_empty()
    }
}

// ============================================================================
// Entry point
// ============================================================================

/// Shows the closing summary of a transaction, and waits for the answer.
///
/// Usually the last screen before signing: `Confirmed` is the person's yes to
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
/// use trezor_app_sdk::modui::{self as ui, ConfirmSummary, ExtraItem, Property};
///
/// fn confirm_total(amount: &str, fee: &str, account: &str) -> trezor_app_sdk::Result<()> {
///     let account_facts = [Property::plain("Account", account)];
///     let extras = [ExtraItem::simple("Account info", &account_facts)];
///
///     ui::confirm_summary(ConfirmSummary::new(
///         "Send",
///         Some(("Amount", amount)),
///         Some(("Fee limit", fee)),
///         "app/summary",
///         &extras,
///     ))?
///     .confirmed()
/// }
/// ```
pub fn confirm_summary(params: ConfirmSummary<'_>) -> Result<UiReply> {
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
        false,                // back_button: sequences run forward only
        params.offers_more(), // external_menu: how the extras are reached
        Some(params.br),      // br_name: the step's name; the app owns it
        BR_CODE_OTHER,        // legacy field; see the constant
    );

    // The summary's own menu holds its way out, but a menu of extras replaces
    // it, so that menu has to carry the way out instead. Without extras the
    // screen keeps its own.
    call(
        &TrezorUiEnum::ConfirmSummary(request),
        params.extras,
        !params.extras.is_empty(),
        Some(params.br),
    )
}

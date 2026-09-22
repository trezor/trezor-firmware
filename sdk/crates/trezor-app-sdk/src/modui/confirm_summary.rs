//! The closing screen of a transaction: what is being spent, and what it costs.
//!
//! # Example
//!
//! ```no_run
//! use trezor_app_sdk::modui::{self as ui, ConfirmSummary};
//!
//! fn confirm_total(amount: &str, fee: &str) -> trezor_app_sdk::Result<()> {
//!     ui::confirm_summary(ConfirmSummary::new(
//!         "Send",
//!         Some(("Amount", amount)),
//!         Some(("Fee limit", fee)),
//!         None,
//!     ))?
//!     .confirmed()
//! }
//! ```

use super::{UiOutcome, call};
use crate::Result;
use crate::structs::{ConfirmSummary as WireConfirmSummary, Property, TrezorUiEnum};

// ============================================================================
// Data types
// ============================================================================

/// Parameters for [`confirm_summary`].
///
/// Unlike most blocks this one carries its extra pages as data rather than
/// through a menu, because the screen itself knows how to present them.
pub struct ConfirmSummary<'a> {
    title: &'a str,
    amount: Option<(&'a str, &'a str)>,
    fee: Option<(&'a str, &'a str)>,
    account: Option<(&'a str, &'a [Property<'a>])>,
}

impl<'a> ConfirmSummary<'a> {
    /// A summary headed `title`.
    ///
    /// `amount` and `fee` are each a label and its value; `account` is the
    /// paying account's title and the facts listed under it.
    pub fn new(
        title: &'a str,
        amount: Option<(&'a str, &'a str)>,
        fee: Option<(&'a str, &'a str)>,
        account: Option<(&'a str, &'a [Property<'a>])>,
    ) -> Self {
        Self {
            title,
            amount,
            fee,
            account,
        }
    }
}

// ============================================================================
// Entry point
// ============================================================================

/// Shows the closing summary of a transaction.
pub fn confirm_summary(params: ConfirmSummary<'_>) -> Result<UiOutcome> {
    let request = WireConfirmSummary::new(
        params.title,
        params.amount.map(|(_, value)| value),
        params.amount.map(|(label, _)| label),
        params.fee.map_or("", |(_, value)| value),
        params.fee.map_or("", |(label, _)| label),
        params.account.map(|(title, _)| title),
        params.account.map(|(_, items)| items),
        None, // extra pages: not exposed until something needs them
        None,
        false, // back_button: sequences run forward only
        None,  // ButtonRequest: emitted on the trusted side, not from here
        0,
    );

    call(&TrezorUiEnum::ConfirmSummary(request))
}

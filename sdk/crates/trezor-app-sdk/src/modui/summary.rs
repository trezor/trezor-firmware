//! The last yes before signing a transfer, in the shape of core's own summary.
//! The public docs live on [`summary`] and [`Summary`].

use crate::modui::{Extra, Field, review};
use crate::{Error, Result};

/// Starts the summary of a transfer: what it costs, as the last yes before the
/// app signs.
///
/// It holds the same values as core's own summary screen (`confirm_summary`):
///
/// | `confirm_summary` | [`Summary`] |
/// |---|---|
/// | `title` | `summary(step, title)` |
/// | `amount`, `amount_label` | [`amount`](Summary::amount) |
/// | `fee`, `fee_label` | [`fee`](Summary::fee) |
/// | `account_items`, `account_title` | [`account`](Summary::account) |
/// | `extra_items`, `extra_title` | [`fee_info`](Summary::fee_info) |
///
/// It is a [`review`] answered by [`Review::confirm_final`](crate::modui::Review::confirm_final):
/// the amount and the fee are its facts, and the account and the fee's details
/// are its extras. A summary needs an amount, a fee, or both; with neither,
/// [`confirm_final`](Summary::confirm_final) is [`Error::DataError`].
///
/// # Example
///
/// ```no_run
/// use trezor_app_sdk::modui::{self, Field};
///
/// fn confirm_send(amount: &str, fee: &str, path: &str) -> trezor_app_sdk::Result<()> {
///     let account = [Field::text("Derivation path", path)];
///     modui::summary("summary", "Send")
///         .amount("Amount", amount, "TRX")
///         .fee("Fee limit", fee, "TRX")
///         .account("Account info", &account)
///         .confirm_final()
/// }
/// ```
pub fn summary<'a>(step: &'a str, title: &'a str) -> Summary<'a> {
    Summary {
        step,
        title,
        amount: None,
        fee: None,
        account: None,
        fee_info: None,
    }
}

/// A transfer's summary, built by [`summary`]. Nothing is shown until
/// [`confirm_final`](Summary::confirm_final) is called.
#[must_use = "a summary shows nothing until `confirm_final` is called"]
pub struct Summary<'a> {
    step: &'a str,
    title: &'a str,
    amount: Option<Field<'a>>,
    fee: Option<Field<'a>>,
    account: Option<Extra<'a>>,
    fee_info: Option<Extra<'a>>,
}

impl<'a> Summary<'a> {
    /// The amount that leaves: its label, its number and its ticker, as
    /// [`Field::amount`] takes them.
    pub fn amount(mut self, label: &'a str, value: &'a str, ticker: &'a str) -> Self {
        self.amount = Some(Field::amount(label, value, ticker));
        self
    }

    /// The fee: its label (`"Fee"`, `"Maximum fee"`, `"Fee limit"`), its
    /// number and its ticker.
    pub fn fee(mut self, label: &'a str, value: &'a str, ticker: &'a str) -> Self {
        self.fee = Some(Field::amount(label, value, ticker));
        self
    }

    /// The account the transfer is signed from, offered in the menu under
    /// `title`. With no facts it is not offered.
    pub fn account(mut self, title: &'a str, fields: &'a [Field<'a>]) -> Self {
        self.account = Some(Extra::new(title, fields));
        self
    }

    /// The fee's details (a gas limit, a fee rate), offered in the menu under
    /// `title`. With no facts it is not offered.
    pub fn fee_info(mut self, title: &'a str, fields: &'a [Field<'a>]) -> Self {
        self.fee_info = Some(Extra::new(title, fields));
        self
    }

    /// Shows the summary as the last yes before the app signs: held on every
    /// model. `Ok(())` for a yes, `Err(Cancelled)` for a no.
    pub fn confirm_final(self) -> Result<()> {
        let mut facts = [Field::note(""); 2];
        let mut count = 0;
        for fact in [self.amount, self.fee].into_iter().flatten() {
            facts[count] = fact;
            count += 1;
        }
        if count == 0 {
            return Err(Error::DataError("a summary needs an amount or a fee"));
        }
        let mut extras = [Extra::new("", &[]); 2];
        let mut offered = 0;
        for extra in [self.account, self.fee_info].into_iter().flatten() {
            extras[offered] = extra;
            offered += 1;
        }
        review(self.step, self.title, &facts[..count])
            .extras(&extras[..offered])
            .confirm_final()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn a_summary_with_neither_amount_nor_fee_is_refused() {
        assert!(matches!(
            summary("summary", "Send").confirm_final(),
            Err(Error::DataError("a summary needs an amount or a fee"))
        ));
    }
}

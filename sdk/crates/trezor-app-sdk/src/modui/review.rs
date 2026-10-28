//! Asking for a yes. The public docs live on [`review`] and [`Review`].
//!
//! A review is a set of facts the person reads before deciding, with at most
//! five extras they can open from its menu. Nothing is shown until the review is
//! confirmed, so a `Review` that is never confirmed is a mistake.

use crate::modui::Field;
use crate::modui::call::{call, yes_or_no};
use crate::modui::field::{check_fields, wire_fields};
use crate::structs::{ReviewRequest, Slice, TrezorUiEnum, WireExtra};
use crate::{Error, Result};

/// How many extras one review may offer: the menu holds six entries, and one of
/// them is the way out.
const MAX_EXTRAS: usize = 5;

/// Builds a set of facts for the person to read, then confirm or refuse.
///
/// Nothing is shown until [`Review::confirm`] or [`Review::confirm_final`] is
/// called. `Review` is `#[must_use]`, so a review that is never confirmed is a
/// compiler warning.
///
/// - `step` — the step name, relative to the app, such as `"send"`; see
///   [step names](crate::modui#step-names).
/// - `title` — the screen's heading, such as `"Send"`.
/// - `fields` — the facts, in the order shown. One fact or many: core pages
///   through them on small screens.
///
/// # Example
///
/// One fact:
///
/// ```no_run
/// use trezor_app_sdk::modui::{self, Field};
///
/// fn confirm_recipient(recipient: &str) -> trezor_app_sdk::Result<()> {
///     modui::review("send", "Send", &[Field::address("Recipient", recipient)]).confirm()
/// }
/// ```
///
/// Several facts on one screen:
///
/// ```no_run
/// use trezor_app_sdk::modui::{self, Field};
///
/// fn confirm_delegate(receiver: &str) -> trezor_app_sdk::Result<()> {
///     modui::review(
///         "delegate",
///         "Delegate",
///         &[
///             Field::address("Recipient", receiver),
///             Field::amount("Amount", "1,000 TRX"),
///             Field::text("Resource", "Energy"),
///         ],
///     )
///     .confirm()
/// }
/// ```
pub fn review<'a>(step: &'a str, title: &'a str, fields: &'a [Field<'a>]) -> Review<'a> {
    Review {
        step,
        title,
        fields,
        extras: [None; MAX_EXTRAS],
        overflow: false,
    }
}

/// A review waiting for its answer: the facts, and the extras offered beside
/// them. See [`review`].
#[must_use = "a review shows nothing until `confirm` or `confirm_final` is called"]
pub struct Review<'a> {
    step: &'a str,
    title: &'a str,
    fields: &'a [Field<'a>],
    extras: [Option<(&'a str, &'a [Field<'a>])>; MAX_EXTRAS],
    // Set when a sixth extra is added, so that `confirm` can refuse the review
    // instead of dropping one without a word.
    overflow: bool,
}

impl<'a> Review<'a> {
    /// Adds facts the person can open from this screen's menu and come back
    /// from, such as the account a payment comes from.
    ///
    /// Optional, and can be called more than once. The person can open extras as
    /// often as they like; only the final decision reaches the app.
    ///
    /// - `label` — the menu entry, and the heading of the screen it opens.
    /// - `fields` — the facts shown when the entry is picked.
    ///
    /// **Limits.** Up to five extras per review: the menu holds six entries and
    /// one is the way out. A sixth one is
    /// [`Error::DataError`](crate::Error::DataError) from `confirm`. Facts per
    /// extra are not limited: core pages through them.
    ///
    /// # Example
    ///
    /// ```no_run
    /// use trezor_app_sdk::modui::{self, Field};
    ///
    /// fn confirm_send(recipient: &str, account_name: &str, path: &str) -> trezor_app_sdk::Result<()> {
    ///     let account = [
    ///         Field::text("Account", account_name),
    ///         Field::text("Derivation path", path),
    ///     ];
    ///     modui::review("send", "Send", &[Field::address("Recipient", recipient)])
    ///         .extra("Account info", &account)
    ///         .confirm()
    /// }
    /// ```
    pub fn extra(mut self, label: &'a str, fields: &'a [Field<'a>]) -> Self {
        match self.extras.iter().position(Option::is_none) {
            Some(slot) => self.extras[slot] = Some((label, fields)),
            None => self.overflow = true,
        }
        self
    }

    /// Shows the review and waits for the answer.
    ///
    /// `Ok(())`: the person said yes and the flow moves on.
    /// `Err(`[`crate::Error::Cancelled`]`)`: they refused, by whatever way
    /// out the model offers. Core draws this as a step ("Continue"), not as the
    /// final decision.
    ///
    /// # Errors
    ///
    /// See [errors](crate::modui#errors).
    ///
    /// # Example
    ///
    /// A warning inside a review:
    ///
    /// ```no_run
    /// use trezor_app_sdk::modui::{self, Field};
    ///
    /// fn confirm_claim(owner: &str) -> trezor_app_sdk::Result<()> {
    ///     modui::review(
    ///         "claim/owner",
    ///         "Claim",
    ///         &[
    ///             Field::address("Owner address", owner),
    ///             Field::warning("This address is not yours."),
    ///         ],
    ///     )
    ///     .confirm()
    /// }
    /// ```
    pub fn confirm(self) -> Result<()> {
        self.decide(false)
    }

    /// Shows the review as the last yes before the app signs or acts.
    ///
    /// Core makes it harder to give by accident: a hold, on every model, with
    /// the menu still there. It is always the same fact screen; an `amount` field
    /// gets the summary styling. The app does not choose a separate "summary"
    /// screen.
    ///
    /// # Errors
    ///
    /// See [errors](crate::modui#errors).
    ///
    /// # Example
    ///
    /// The closing amount and fee:
    ///
    /// ```no_run
    /// use trezor_app_sdk::modui::{self, Field};
    ///
    /// fn confirm_send(amount: &str, fee: &str) -> trezor_app_sdk::Result<()> {
    ///     modui::review(
    ///         "summary",
    ///         "Send",
    ///         &[Field::amount("Amount", amount), Field::amount("Fee limit", fee)],
    ///     )
    ///     .confirm_final()
    /// }
    /// ```
    pub fn confirm_final(self) -> Result<()> {
        self.decide(true)
    }

    fn decide(self, is_final: bool) -> Result<()> {
        if self.overflow {
            return Err(Error::DataError("more than 5 extras"));
        }
        check_fields(self.fields)?;
        let extras: [WireExtra<'a>; MAX_EXTRAS] = core::array::from_fn(|i| match self.extras[i] {
            Some((label, fields)) => WireExtra {
                label: label.into(),
                fields: wire_fields(fields),
            },
            None => WireExtra {
                label: "".into(),
                fields: Slice::new(&[]),
            },
        });
        let used = self.extras.iter().flatten().count();
        let request = ReviewRequest {
            step: self.step.into(),
            title: self.title.into(),
            fields: wire_fields(self.fields),
            extras: Slice::new(&extras[..used]),
            is_final,
        };
        yes_or_no(call(TrezorUiEnum::Review(request)))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn extras_fill_the_free_slots_in_order() {
        let facts = [Field::text("a", "b")];
        let review = review("step", "title", &facts)
            .extra("one", &facts)
            .extra("two", &facts);
        assert_eq!(review.extras.iter().flatten().count(), 2);
        assert_eq!(review.extras[0].map(|(label, _)| label), Some("one"));
        assert_eq!(review.extras[1].map(|(label, _)| label), Some("two"));
        assert!(!review.overflow);
    }

    #[test]
    fn a_sixth_extra_is_recorded_as_an_overflow() {
        let facts = [Field::text("a", "b")];
        let mut review = review("step", "title", &facts);
        for _ in 0..MAX_EXTRAS {
            review = review.extra("again", &facts);
        }
        assert!(!review.overflow);
        assert!(review.extra("too many", &facts).overflow);
    }
}

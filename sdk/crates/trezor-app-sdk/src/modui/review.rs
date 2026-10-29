//! Asking for a yes. The public docs live on [`review`], [`Review`] and
//! [`Extra`].
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

/// Facts the person can open from a review's menu, under a label of their own.
///
/// An extra with no facts is not offered: there is nothing to show in it. Build
/// one from an `Option` when the facts may be missing, and let it drop:
///
/// ```no_run
/// use trezor_app_sdk::modui::{Extra, Field};
///
/// let refund = Some("TQ9JfxgJ9JBz4GZ4MRDrjJeBdA6Mx5yYhq");
/// let refund = refund.map(|address| Field::address("Refund address", address));
/// let extra = Extra::new("Refund", refund.as_slice());
/// ```
///
/// `Extra` is a `#[repr(transparent)]` wrapper around the wire's extra, the way
/// [`Field`] is around the wire's fact, so a slice of extras has the layout of a
/// slice of wire extras.
#[derive(Copy, Clone)]
#[repr(transparent)]
pub struct Extra<'a> {
    wire: WireExtra<'a>,
}

impl<'a> Extra<'a> {
    /// The menu entry, the heading of the screen it opens, and the facts shown
    /// when it is picked.
    ///
    /// # Example
    ///
    /// ```no_run
    /// use trezor_app_sdk::modui::{Extra, Field};
    ///
    /// let account = [
    ///     Field::text("Account", "TRX #1"),
    ///     Field::text("Derivation path", "m/44'/195'/0'/0/0"),
    /// ];
    /// let info = Extra::new("Account info", &account);
    /// ```
    pub fn new(label: &'a str, fields: &'a [Field<'a>]) -> Self {
        Self {
            wire: WireExtra {
                label: label.into(),
                fields: wire_fields(fields),
            },
        }
    }
}

/// The extras a request carries: the ones with facts, in order.
///
/// An extra with no facts is not offered, so it is dropped here rather than sent
/// as a blank menu entry. Returns the wire extras and how many there are; the rest
/// of the array is padding.
fn offered_extras<'a>(extras: &'a [Extra<'a>]) -> Result<([WireExtra<'a>; MAX_EXTRAS], usize)> {
    let empty = WireExtra {
        label: "".into(),
        fields: Slice::new(&[]),
    };
    let mut kept = [empty; MAX_EXTRAS];
    let mut used = 0;
    for extra in extras {
        if extra.wire.fields.as_slice().is_empty() {
            continue;
        }
        if used == MAX_EXTRAS {
            return Err(Error::DataError("more than 5 extras"));
        }
        kept[used] = extra.wire;
        used += 1;
    }
    Ok((kept, used))
}

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
        extras: &[],
    }
}

/// A review waiting for its answer: the facts, and the extras offered beside
/// them. See [`review`].
#[must_use = "a review shows nothing until `confirm` or `confirm_final` is called"]
pub struct Review<'a> {
    step: &'a str,
    title: &'a str,
    fields: &'a [Field<'a>],
    extras: &'a [Extra<'a>],
}

impl<'a> Review<'a> {
    /// Facts the person can open from this screen's menu and come back from,
    /// such as the account a payment comes from.
    ///
    /// Optional, and replaces any extras set before. The person can open extras as
    /// often as they like; only the final decision reaches the app.
    ///
    /// - `extras` — one [`Extra`] per menu entry: its label, and the facts shown
    ///   when it is picked. An extra with no facts is not offered.
    ///
    /// **Limits.** Up to five offered extras per review: the menu holds six
    /// entries and one is the way out. A sixth one is
    /// [`Error::DataError`](crate::Error::DataError) from `confirm`. Facts per
    /// extra are not limited: core pages through them.
    ///
    /// # Example
    ///
    /// ```no_run
    /// use trezor_app_sdk::modui::{self, Extra, Field};
    ///
    /// fn confirm_send(recipient: &str, account_name: &str, path: &str) -> trezor_app_sdk::Result<()> {
    ///     let account = [
    ///         Field::text("Account", account_name),
    ///         Field::text("Derivation path", path),
    ///     ];
    ///     modui::review("send", "Send", &[Field::address("Recipient", recipient)])
    ///         .extras(&[Extra::new("Account info", &account)])
    ///         .confirm()
    /// }
    /// ```
    pub fn extras(mut self, extras: &'a [Extra<'a>]) -> Self {
        self.extras = extras;
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
        let (extras, used) = offered_extras(self.extras)?;
        check_fields(self.fields)?;
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
    fn the_extras_slice_is_passed_through() {
        let facts = [Field::text("a", "b")];
        let extras = [Extra::new("one", &facts), Extra::new("two", &facts)];
        let (wire, used) = offered_extras(&extras).unwrap();
        assert_eq!(used, 2);
        assert_eq!(wire[0].label.as_str(), "one");
        assert_eq!(wire[1].label.as_str(), "two");
        assert_eq!(wire[0].fields.as_slice().len(), 1);
    }

    #[test]
    fn an_empty_extra_is_not_offered() {
        let facts = [Field::text("a", "b")];
        let extras = [
            Extra::new("empty", &[]),
            Extra::new("full", &facts),
            Extra::new("also empty", &[]),
        ];
        let (wire, used) = offered_extras(&extras).unwrap();
        assert_eq!(used, 1);
        assert_eq!(wire[0].label.as_str(), "full");
    }

    #[test]
    fn a_sixth_offered_extra_is_refused() {
        let facts = [Field::text("a", "b")];
        let extras = [Extra::new("again", &facts); 6];
        assert!(matches!(
            offered_extras(&extras),
            Err(Error::DataError("more than 5 extras"))
        ));
    }

    #[test]
    fn five_offered_extras_beside_an_empty_one_are_accepted() {
        let facts = [Field::text("a", "b")];
        let extras = [
            Extra::new("one", &facts),
            Extra::new("two", &facts),
            Extra::new("three", &facts),
            Extra::new("four", &facts),
            Extra::new("five", &facts),
            Extra::new("empty", &[]),
        ];
        let (_, used) = offered_extras(&extras).unwrap();
        assert_eq!(used, MAX_EXTRAS);
    }
}

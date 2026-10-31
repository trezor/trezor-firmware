//! Asking for a yes. The public docs live on [`review`], [`Review`] and
//! [`Extra`].
//!
//! A review is a set of facts the person reads before deciding, with at most
//! five extras they can open from its menu. Nothing is shown until the review is
//! answered, so a `Review` that is never answered is a mistake.

use crate::modui::Field;
use crate::modui::call::{call, yes_or_no};
use crate::modui::field::{check_fields, wire_fields};
use crate::structs::{FieldsRequest, ReviewRequest, Slice, TrezorUiEnum, WireExtra};
use crate::{Error, Result};

/// How many extras one review may offer: the menu holds six entries, and one of
/// them is the way out.
const MAX_EXTRAS: usize = 5;

/// Facts the person can open from a review's menu, under a label of their own.
///
/// An extra may hold a [`data`](Field::data) field like a review's own facts:
/// core pulls it while the person pages through it. A field built from
/// [`data_source`](Field::data_source) may not sit in an extra: an extra can be
/// opened again, and its bytes would be read again.
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
        let fields = extra.wire.fields.as_slice();
        if fields.is_empty() {
            continue;
        }
        if used == MAX_EXTRAS {
            return Err(Error::DataError("more than 5 extras"));
        }
        if fields.iter().any(|field| field.is_streamed()) {
            return Err(Error::DataError(
                "a streamed data field cannot be in an extra",
            ));
        }
        kept[used] = extra.wire;
        used += 1;
    }
    Ok((kept, used))
}

/// Refuses extras on a danger: its menu already holds the way forward, so there
/// is no room for entries of the app's.
///
/// The same rule as [`offered_extras`], the other way round: an extra with no
/// facts is not offered, so it is fine and dropped; one with facts is the app's
/// mistake.
fn check_no_extras(extras: &[Extra<'_>]) -> Result<()> {
    if extras
        .iter()
        .any(|extra| !extra.wire.fields.as_slice().is_empty())
    {
        return Err(Error::DataError("a danger offers no extras"));
    }
    Ok(())
}

/// Builds a set of facts for the person to read, then confirm or refuse.
///
/// Nothing is shown until [`Review::confirm`], [`Review::confirm_final`] or
/// [`Review::confirm_danger`] is called. `Review` is `#[must_use]`, so a review
/// that is never answered is a compiler warning.
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
///             Field::amount("Amount", "1,000", "TRX"),
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
#[must_use = "a review shows nothing until `confirm`, `confirm_final` or `confirm_danger` is called"]
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
    /// [`Error::DataError`](crate::Error::DataError) from `confirm`, and any
    /// offered extra is one from `confirm_danger`, whose menu is full. Facts per
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
    /// The plainest yes of the three: a tap, with the menu still there for the
    /// extras and the way out.
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
    /// Harder than [`Review::confirm`]: core makes it harder to give by
    /// accident, with a hold on every model, and the menu still there. It is
    /// always the same fact screen; an `amount` field gets the summary styling.
    /// The app does not choose a separate "summary" screen.
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
    ///         &[
    ///             Field::amount("Amount", amount, "TRX"),
    ///             Field::amount("Fee limit", fee, "TRX"),
    ///         ],
    ///     )
    ///     .confirm_final()
    /// }
    /// ```
    pub fn confirm_final(self) -> Result<()> {
        self.decide(true)
    }

    /// Shows the review as a danger: what is risky, before the person goes on.
    ///
    /// The hardest of the three to reach: neither a tap nor a hold but a
    /// deliberate detour, so going on is never one press away. Refusing is the
    /// default, and `Ok(())` only if the person chooses to go on. The facts are
    /// the ones a review would show, so the screen can say *what* is risky, such
    /// as the unknown contract's address: usually a [`Field::note`] that says
    /// what the risk is, and the value it concerns.
    ///
    /// **No extras.** A danger's menu already holds the way forward, so there is
    /// no room for entries of the app's: an extra with no facts is fine and
    /// dropped, the way a review drops it, and one with facts is
    /// [`Error::DataError`](crate::Error::DataError).
    ///
    /// # Errors
    ///
    /// See [errors](crate::modui#errors).
    ///
    /// # Example
    ///
    /// An unknown contract:
    ///
    /// ```no_run
    /// use trezor_app_sdk::modui::{self, Field};
    ///
    /// fn warn_unknown_contract(contract_address: &str) -> trezor_app_sdk::Result<()> {
    ///     modui::review(
    ///         "unknown_contract",
    ///         "Important",
    ///         &[
    ///             Field::note("This contract is unknown. Continue only if you trust it."),
    ///             Field::address("Contract", contract_address),
    ///         ],
    ///     )
    ///     .confirm_danger()
    /// }
    /// ```
    ///
    /// An unusual derivation path:
    ///
    /// ```no_run
    /// use trezor_app_sdk::modui::{self, Field};
    ///
    /// fn warn_unknown_path(path: &str) -> trezor_app_sdk::Result<()> {
    ///     modui::review(
    ///         "path_warning",
    ///         "Unknown path",
    ///         &[
    ///             Field::note("This path is not usual for this coin."),
    ///             Field::text("Derivation path", path),
    ///         ],
    ///     )
    ///     .confirm_danger()
    /// }
    /// ```
    pub fn confirm_danger(self) -> Result<()> {
        yes_or_no(call(TrezorUiEnum::Danger(self.danger_request()?)))
    }

    /// The danger request this review would send, once the app's mistakes are
    /// refused: an offered extra, or a bad set of facts.
    fn danger_request(self) -> Result<FieldsRequest<'a>> {
        check_no_extras(self.extras)?;
        check_fields(self.fields)?;
        Ok(FieldsRequest {
            step: self.step.into(),
            title: self.title.into(),
            fields: wire_fields(self.fields),
        })
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

    #[test]
    fn a_danger_refuses_an_offered_extra() {
        let facts = [Field::text("a", "b")];
        assert!(matches!(
            review("step", "title", &facts)
                .extras(&[Extra::new("a", &facts)])
                .confirm_danger(),
            Err(Error::DataError("a danger offers no extras"))
        ));
    }

    #[test]
    fn a_danger_checks_its_extras_before_its_facts() {
        let facts = [Field::data("a", &[1]), Field::data("b", &[2])];
        assert!(matches!(
            review("step", "title", &facts)
                .extras(&[Extra::new("a", &facts)])
                .confirm_danger(),
            Err(Error::DataError("a danger offers no extras"))
        ));
    }

    #[test]
    fn a_danger_accepts_empty_extras() {
        let facts = [Field::text("a", "b")];
        let extras = [Extra::new("empty", &[])];
        let request = review("step", "title", &facts)
            .extras(&extras)
            .danger_request()
            .unwrap();
        assert_eq!(request.step.as_str(), "step");
        assert_eq!(request.title.as_str(), "title");
        assert_eq!(request.fields.as_slice().len(), 1);
    }

    #[test]
    fn a_streamed_field_in_an_extra_is_refused() {
        let bytes: &[u8] = &[0u8; 8];
        let stream = [Field::data_source("stream", bytes.len() as u32, &bytes)];
        assert!(matches!(
            offered_extras(&[Extra::new("extra", &stream)]),
            Err(Error::DataError(
                "a streamed data field cannot be in an extra"
            ))
        ));
    }
}

//! Asking for a yes. The public docs live on [`review`], [`Review`] and
//! [`Extra`].
//!
//! A review is a set of facts the person reads before answering, with extras
//! they can open from its menu. Nothing is shown until the review is answered,
//! so a `Review` that is never answered is a mistake.

use crate::modui::Field;
use crate::modui::call::{call, confirmed};
use crate::modui::field::{check_fields, wire_fields};
use crate::structs::{Answer, ReviewRequest, Slice, TrezorUiEnum, TrezorUiResult, WireExtra};
use crate::{Error, Result};

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

    fn fields(&self) -> &'a [Field<'a>] {
        // SAFETY: `fields` was built by `wire_fields` from a `&[Field]`, and
        // `Field` is `#[repr(transparent)]` over `WireField`.
        let wire = self.wire.fields.as_slice();
        unsafe { core::slice::from_raw_parts(wire.as_ptr().cast::<Field<'a>>(), wire.len()) }
    }
}

/// The extras as a request carries them.
///
/// `Extra` is a `#[repr(transparent)]` wrapper around `WireExtra`, so the two
/// lists have the same layout and the borrow is only a cast.
fn wire_extras<'a>(extras: &'a [Extra<'a>]) -> Slice<'a, WireExtra<'a>> {
    // SAFETY: `Extra` is `#[repr(transparent)]` over `WireExtra`, so a
    // `&[Extra]` has the layout of a `&[WireExtra]` of the same length.
    let wire = unsafe {
        core::slice::from_raw_parts(extras.as_ptr().cast::<WireExtra<'a>>(), extras.len())
    };
    Slice::new(wire)
}

/// Refuses what core cannot draw for `answer`, before anything is sent: more
/// offered extras than its menu has room for, too many `data` fields in one
/// list of facts, or a streamed `data` field in an extra.
///
/// An extra with no facts is not offered, so it does not count; core drops it.
fn check_request(fields: &[Field<'_>], extras: &[Extra<'_>], answer: Answer) -> Result<()> {
    let offered = extras.iter().filter(|extra| !extra.fields().is_empty());
    if offered.clone().count() > answer.max_extras() {
        return Err(Error::DataError("more extras than the menu has room for"));
    }
    check_fields(fields)?;
    for extra in offered {
        check_fields(extra.fields())?;
        if extra.fields().iter().any(Field::is_streamed) {
            return Err(Error::DataError(
                "a streamed data field cannot be in an extra",
            ));
        }
    }
    Ok(())
}

/// Builds a set of facts for the person to read, then answer.
///
/// Nothing is shown until the review is answered, by [`Review::confirm`],
/// [`Review::confirm_strong`], [`Review::confirm_danger`] or
/// [`Review::details`]. `Review` is `#[must_use]`, so a review that is never
/// answered is a compiler warning.
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

/// The answer to [`Review::details`]: whether the person wants to see the
/// details.
///
/// Named rather than a `bool`, because refusing is a third answer, and it is
/// [`Error::Cancelled`](crate::Error::Cancelled).
#[derive(Copy, Clone, PartialEq, Eq)]
pub enum Details {
    /// The person wants to see the details.
    Show,
    /// The person accepts without seeing them.
    Skip,
}

/// A review waiting for its answer: the facts, and the extras offered beside
/// them. See [`review`].
#[must_use = "a review shows nothing until it is answered"]
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
    /// often as they like; only the final answer reaches the app.
    ///
    /// - `extras` — one [`Extra`] per menu entry: its label, and the facts shown
    ///   when it is picked. An extra with no facts is not offered.
    ///
    /// **Limits.** Every entry of the menu counts against
    /// [`MAX_MENU_ENTRIES`](crate::structs::MAX_MENU_ENTRIES): each offered extra
    /// takes one, the way out takes one, and [`details`](Review::details)' "Show
    /// all" takes one more. So [`confirm`](Review::confirm) and
    /// [`confirm_strong`](Review::confirm_strong) offer up to five extras,
    /// `details` up to four, and [`confirm_danger`](Review::confirm_danger) none,
    /// because its menu holds the way forward. More is
    /// [`Error::DataError`](crate::Error::DataError) from the answer. Facts per
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
    /// The plainest yes: a tap, with the menu there for the extras and the way
    /// out. Core draws it as a step ("Continue"), not as the final decision.
    ///
    /// `Ok(())`: the person said yes and the flow moves on.
    /// `Err(`[`crate::Error::Cancelled`]`)`: they refused, by whatever way out
    /// the model offers.
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
        confirmed(self.send(Answer::Confirm)?)
    }

    /// Shows the review as the strong yes: a deliberate confirmation, usable
    /// mid-flow, before the app signs or acts.
    ///
    /// Harder to give by accident than [`Review::confirm`]: drawn as a hold
    /// where the model has one, with the menu still there. For a transfer's
    /// closing amount and fee, [`summary`](crate::modui::summary) builds this
    /// review for you.
    ///
    /// # Errors
    ///
    /// See [errors](crate::modui#errors).
    ///
    /// # Example
    ///
    /// ```no_run
    /// use trezor_app_sdk::modui::{self, Field};
    ///
    /// fn confirm_vote(candidate: &str) -> trezor_app_sdk::Result<()> {
    ///     modui::review("vote", "Vote", &[Field::address("Candidate", candidate)])
    ///         .confirm_strong()
    /// }
    /// ```
    pub fn confirm_strong(self) -> Result<()> {
        confirmed(self.send(Answer::Strong)?)
    }

    /// Shows the review as a danger: what is risky, before the person goes on.
    ///
    /// The hardest yes to reach: neither a tap nor a hold but a deliberate
    /// detour, so going on is never one press away. Refusing is the default, and
    /// `Ok(())` only if the person chooses to go on. The facts say *what* is
    /// risky: usually a [`Field::note`] that says what the risk is, and the value
    /// it concerns.
    ///
    /// **No extras.** A danger's menu already holds the way forward, so there is
    /// no room for entries of the app's: an extra with no facts is dropped, the
    /// way a review drops it, and one with facts is
    /// [`Error::DataError`](crate::Error::DataError).
    ///
    /// # Errors
    ///
    /// See [errors](crate::modui#errors).
    ///
    /// # Example
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
    pub fn confirm_danger(self) -> Result<()> {
        confirmed(self.send(Answer::Danger)?)
    }

    /// Shows the short version and offers the details, which the person may
    /// skip.
    ///
    /// An ordinary review of the facts, whose menu also holds "Show all". An
    /// extra is a peek that comes back to the review; "Show all" ends the review
    /// and branches the flow. Confirming accepts the short version.
    ///
    /// `Ok(`[`Details::Show`]`)`: the person picked "Show all".
    /// `Ok(`[`Details::Skip`]`)`: they confirmed without the details.
    /// `Err(`[`crate::Error::Cancelled`]`)`: they refused.
    ///
    /// # Errors
    ///
    /// See [errors](crate::modui#errors).
    ///
    /// # Example
    ///
    /// ```no_run
    /// use trezor_app_sdk::modui::{self, Details, Field};
    ///
    /// fn confirm_typed_data(primary_type: &str, keys_summary: &str) -> trezor_app_sdk::Result<()> {
    ///     let facts = [
    ///         Field::text("Type", primary_type),
    ///         Field::text("Contains", keys_summary),
    ///     ];
    ///     match modui::review("typed_data/message", "Confirm message", &facts).details()? {
    ///         Details::Show => { /* walk the message, one review per member */ }
    ///         Details::Skip => {}
    ///     }
    ///     Ok(())
    /// }
    /// ```
    pub fn details(self) -> Result<Details> {
        match self.send(Answer::Details)? {
            TrezorUiResult::ShowDetails => Ok(Details::Show),
            TrezorUiResult::Confirmed => Ok(Details::Skip),
            TrezorUiResult::Cancelled => Err(Error::Cancelled),
        }
    }

    /// The request this review sends for `answer`, once the app's mistakes
    /// are refused.
    fn request(&self, answer: Answer) -> Result<ReviewRequest<'a>> {
        check_request(self.fields, self.extras, answer)?;
        Ok(ReviewRequest {
            step: self.step.into(),
            title: self.title.into(),
            fields: wire_fields(self.fields),
            extras: wire_extras(self.extras),
            answer,
        })
    }

    fn send(self, answer: Answer) -> Result<TrezorUiResult> {
        call(TrezorUiEnum::Review(self.request(answer)?))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Six extras, the first `count` of them offered and the rest empty.
    fn offered<'a>(facts: &'a [Field<'a>], count: usize) -> [Extra<'a>; 6] {
        core::array::from_fn(|i| {
            if i < count {
                Extra::new("extra", facts)
            } else {
                Extra::new("empty", &[])
            }
        })
    }

    #[test]
    fn the_extras_are_passed_through_as_built() {
        let facts = [Field::text("a", "b")];
        let extras = [Extra::new("one", &facts), Extra::new("two", &facts)];
        let request = review("step", "title", &facts)
            .extras(&extras)
            .request(Answer::Confirm)
            .unwrap();
        let wire = request.extras.as_slice();
        assert_eq!(wire.len(), 2);
        assert_eq!(wire[0].label.as_str(), "one");
        assert_eq!(wire[1].label.as_str(), "two");
        assert_eq!(wire[0].fields.len(), 1);
    }

    #[test]
    fn each_answer_has_its_own_room_for_extras() {
        let facts = [Field::text("a", "b")];
        for (answer, room) in [
            (Answer::Confirm, 5),
            (Answer::Strong, 5),
            (Answer::Details, 4),
            (Answer::Danger, 0),
        ] {
            let fits = offered(&facts, room);
            assert!(
                review("s", "t", &facts)
                    .extras(&fits)
                    .request(answer)
                    .is_ok()
            );
            let more = offered(&facts, room + 1);
            assert!(matches!(
                review("s", "t", &facts).extras(&more).request(answer),
                Err(Error::DataError("more extras than the menu has room for"))
            ));
        }
    }

    #[test]
    fn an_empty_extra_does_not_count() {
        let facts = [Field::text("a", "b")];
        let extras = offered(&facts, 0);
        assert!(
            review("s", "t", &facts)
                .extras(&extras)
                .request(Answer::Danger)
                .is_ok()
        );
    }

    #[test]
    fn an_extra_holds_at_most_one_data_field() {
        let facts = [Field::text("a", "b")];
        let data = [Field::data("a", &[1]), Field::data("b", &[2])];
        assert!(matches!(
            review("s", "t", &facts)
                .extras(&[Extra::new("data", &data)])
                .request(Answer::Confirm),
            Err(Error::DataError("more than one data field"))
        ));
    }

    #[test]
    fn a_streamed_field_in_an_extra_is_refused() {
        let facts = [Field::text("a", "b")];
        let bytes: &[u8] = &[0u8; 8];
        let stream = [Field::data_source("stream", bytes.len() as u32, &bytes)];
        assert!(matches!(
            review("s", "t", &facts)
                .extras(&[Extra::new("extra", &stream)])
                .request(Answer::Confirm),
            Err(Error::DataError(
                "a streamed data field cannot be in an extra"
            ))
        ));
    }
}

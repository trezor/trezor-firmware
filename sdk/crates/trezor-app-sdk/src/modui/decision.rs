//! Decisions that are not a plain yes. The public docs live on [`danger`] and
//! [`details`].
//!
//! Both take the same facts a review would show; they differ in what the answer
//! can be. Going on after a `danger` takes a deliberate extra step, and a
//! `details` screen lets the person skip what it offers.

use crate::modui::Field;
use crate::modui::call::{call, yes_or_no};
use crate::modui::field::{check_fields, wire_fields};
use crate::structs::{FieldsRequest, TrezorUiEnum, TrezorUiResult};
use crate::{Error, Result};

/// Asks the person to go on with something risky, and waits for the answer.
///
/// Refusing is the default, and continuing takes a deliberate extra step.
/// `Ok(())` only if the person chooses to go on. It takes fields, so the screen
/// can show *what* is risky, such as the unknown contract's address. Usually a
/// [`Field::note`] that says what the risk is, and the value it concerns.
///
/// - `step` — the step name, relative to the app, such as
///   `"unknown_contract"`; see
///   [step names](crate::modui#step-names).
/// - `title` — the screen's heading, such as `"Important"`.
/// - `fields` — what is risky, in the order shown.
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
///     modui::danger(
///         "unknown_contract",
///         "Important",
///         &[
///             Field::note("This contract is unknown. Continue only if you trust it."),
///             Field::address("Contract", contract_address),
///         ],
///     )
/// }
/// ```
///
/// ```no_run
/// use trezor_app_sdk::modui::{self, Field};
///
/// fn warn_unknown_path(path: &str) -> trezor_app_sdk::Result<()> {
///     modui::danger(
///         "path_warning",
///         "Unknown path",
///         &[
///             Field::note("This path is not usual for this coin."),
///             Field::text("Derivation path", path),
///         ],
///     )
/// }
/// ```
pub fn danger<'a>(step: &'a str, title: &'a str, fields: &'a [Field<'a>]) -> Result<()> {
    check_fields(fields)?;
    let request = FieldsRequest {
        step: step.into(),
        title: title.into(),
        fields: wire_fields(fields),
    };
    yes_or_no(call(TrezorUiEnum::Danger(request)))
}

/// The answer to [`details`]: whether the person wants to see the details.
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

/// Offers details the person may skip, and waits for the answer.
///
/// One screen with three answers: show the details, skip them, or refuse. The
/// answer is named (`Details::Show` / `Details::Skip`); refusing is
/// `Err(`[`crate::Error::Cancelled`]`)`. `fields` is the short version the
/// person sees before deciding.
///
/// - `step` — the step name, relative to the app, such as
///   `"typed_data/message"`; see
///   [step names](crate::modui#step-names).
/// - `title` — the screen's heading, such as `"Confirm message"`.
/// - `fields` — the short version shown before the choice.
///
/// **Per model today.** Delizia and Eckhart can draw this screen
/// (`should_show_more`), and Caesar can with PR #8045. Bolt needs one.
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
///     match modui::details(
///         "typed_data/message",
///         "Confirm message",
///         &[
///             Field::text("Type", primary_type),
///             Field::text("Contains", keys_summary),
///         ],
///     )? {
///         Details::Show => { /* walk the message, one review per member */ }
///         Details::Skip => {}
///     }
///     Ok(())
/// }
/// ```
pub fn details<'a>(step: &'a str, title: &'a str, fields: &'a [Field<'a>]) -> Result<Details> {
    check_fields(fields)?;
    let request = FieldsRequest {
        step: step.into(),
        title: title.into(),
        fields: wire_fields(fields),
    };
    match call(TrezorUiEnum::Details(request)) {
        TrezorUiResult::ShowDetails => Ok(Details::Show),
        TrezorUiResult::Confirmed => Ok(Details::Skip),
        TrezorUiResult::Cancelled => Err(Error::Cancelled),
        _ => Err(Error::DataError("unexpected UI answer")),
    }
}

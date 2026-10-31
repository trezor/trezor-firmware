//! One decision that is not a plain yes. The public docs live on [`details`].
//!
//! It takes the same facts a review would show, and differs in what the answer
//! can be: it lets the person skip what it offers. A danger is a review's
//! answer, [`Review::confirm_danger`](crate::modui::Review::confirm_danger).

use crate::modui::Field;
use crate::modui::call::{call, take_source_error};
use crate::modui::field::{check_fields, wire_fields};
use crate::structs::{FieldsRequest, TrezorUiEnum, TrezorUiResult};
use crate::{Error, Result};

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
        TrezorUiResult::Cancelled => Err(take_source_error().unwrap_or(Error::Cancelled)),
    }
}

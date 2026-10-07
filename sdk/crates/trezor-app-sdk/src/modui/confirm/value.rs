//! Confirming a single value. The public docs live on [`value`].
//!
//! WIP: manual test results with extras (by hand):
//! - caesar (T3B1): only the value is drawn. Its Cancel works, but there is
//!   no menu, so the extras cannot be reached.
//! - delizia (T3T1): the menu button replaced the screen's way out and the
//!   menu had none, so the block could not be refused. delizia's menu now
//!   adds its own Cancel; not re-tested since.
//! - bolt (T2T1): no menu, so the extras cannot be reached.

use crate::Result;
use crate::modui::internal::{BR_CODE_OTHER, call, decide};
use crate::modui::{Commitment, Decision, ExtraItem};
use crate::traits::ui::ConfirmValue as WireConfirmValue;

// ============================================================================
// Data types
// ============================================================================

/// What the value *is*, which is what decides how it is formatted.
///
/// The app says which kind it has; the library decides what that looks like.
/// There is deliberately no `chunkify` flag: grouping an address into chunks is
/// a consequence of it being an address, not a separate choice.
#[derive(Copy, Clone, PartialEq, Eq)]
pub enum ValueKind {
    /// Shown as written.
    Text,
    /// Grouped into chunks so it can be compared by eye.
    Address,
}

/// A note along the bottom of the screen.
///
/// Two variants rather than a string plus a flag, so the caller names what the
/// note means and the library picks how loud it looks.
#[derive(Copy, Clone)]
pub enum Footer<'a> {
    /// Ordinary guidance.
    Hint(&'a str),
    /// Something the person should weigh before confirming.
    Warning(&'a str),
}

/// Parameters for [`value`], built by [`Value::new`].
pub struct Value<'a> {
    title: &'a str,
    value: &'a str,
    kind: ValueKind,
    subtitle: Option<&'a str>,
    description: Option<&'a str>,
    footer: Option<Footer<'a>>,
    commitment: Commitment,
    br: &'a str,
    extras: &'a [ExtraItem<'a>],
}

impl<'a> Value<'a> {
    /// Confirms one `value` of the given kind under `title`.
    ///
    /// - `title` — the screen's heading, such as `"Send"`.
    /// - `value` — the value itself, shown verbatim.
    /// - `kind` — what the value is, which decides how it is formatted.
    /// - `subtitle` — optional line under the heading, such as `"Recipient"`.
    /// - `description` — optional text above the value.
    /// - `footer` — optional note along the bottom of the screen.
    /// - `commitment` — whether confirming this is the person's final yes; see
    ///   [`Commitment`].
    /// - `br` — the step name the host sees; see
    ///   [step names](crate::modui#step-names).
    /// - `extras` — more the person can look at from this screen; see
    ///   [extras](crate::modui#extras-and-the-way-out).
    #[allow(clippy::too_many_arguments)]
    pub fn new(
        title: &'a str,
        value: &'a str,
        kind: ValueKind,
        subtitle: Option<&'a str>,
        description: Option<&'a str>,
        footer: Option<Footer<'a>>,
        commitment: Commitment,
        br: &'a str,
        extras: &'a [ExtraItem<'a>],
    ) -> Self {
        Self {
            title,
            value,
            kind,
            subtitle,
            description,
            footer,
            commitment,
            br,
            extras,
        }
    }
}

// ============================================================================
// Entry point
// ============================================================================

/// Asks the person to confirm one value, and waits for the answer.
///
/// The person can always refuse, so the block takes no `cancel`: the way out
/// is on the screen, or in its menu where the menu button takes its place.
///
/// # Errors
///
/// See [errors](crate::modui#errors).
///
/// # Example
///
/// ```no_run
/// use trezor_app_sdk::modui::{Commitment, confirm};
///
/// fn confirm_recipient(address: &str) -> trezor_app_sdk::Result<()> {
///     confirm::value(confirm::Value::new(
///         "Send",
///         address,
///         confirm::ValueKind::Address,
///         Some("Recipient"),
///         None,
///         Some(confirm::Footer::Hint("Check with the source.")),
///         Commitment::Step,
///         "app/send/recipient",
///         &[],
///     ))?
///     .confirmed()
/// }
/// ```
pub fn value(params: Value<'_>) -> Result<Decision> {
    let footer = params.footer.map(|f| match f {
        Footer::Hint(text) => (text, false),
        Footer::Warning(text) => (text, true),
    });

    let request = WireConfirmValue::new(
        params.title,
        params.value,
        params.description,
        Some(params.br), // br_name: the step's name; the app owns it (see the field docs)
        BR_CODE_OTHER,   // legacy field; see the constant
        true,            // is_data: values are shown verbatim, not prose
        None,            // verb: the label follows the gesture, which the block owns
        params.subtitle,
        false, // info: the menu button is the external one below
        params.commitment == Commitment::Final, // hold: follows from the commitment
        params.kind == ValueKind::Address,
        false,                     // page_counter
        !params.extras.is_empty(), // external_menu: how the menu is reached
        footer,
    );

    decide(call(&request, params.extras, Some(params.br))?)
}

//! Confirming a single value. The public docs live on [`confirm_value`].

use super::extra::ExtraItem;
use super::{BR_CODE_OTHER, Commitment, UiOutcome, call};
use crate::Result;
use crate::structs::{ConfirmValue as WireConfirmValue, TrezorUiEnum};

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

/// Parameters for [`confirm_value`], built by [`ConfirmValue::new`].
pub struct ConfirmValue<'a> {
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

impl<'a> ConfirmValue<'a> {
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

    /// Whether the screen has anything to offer besides its main content.
    fn offers_more(&self) -> bool {
        !self.extras.is_empty()
    }
}

// ============================================================================
// Entry point
// ============================================================================

/// Asks the person to confirm one value, and waits for the answer.
///
/// The person can always refuse: the screen has its own way out, so the block
/// takes no `cancel`.
///
/// # Errors
///
/// See [errors](crate::modui#errors).
///
/// # Example
///
/// ```no_run
/// use trezor_app_sdk::modui::{self as ui, Commitment, ConfirmValue, Footer, ValueKind};
///
/// fn confirm_recipient(address: &str) -> trezor_app_sdk::Result<()> {
///     ui::confirm_value(ConfirmValue::new(
///         "Send",
///         address,
///         ValueKind::Address,
///         Some("Recipient"),
///         None,
///         Some(Footer::Hint("Check with the source.")),
///         Commitment::Step,
///         "app/send/recipient",
///         &[],
///     ))?
///     .confirmed()
/// }
/// ```
pub fn confirm_value(params: ConfirmValue<'_>) -> Result<UiOutcome> {
    let footer = params.footer.map(|f| match f {
        Footer::Hint(text) => (text, false),
        Footer::Warning(text) => (text, true),
    });

    let request = TrezorUiEnum::ConfirmValue(WireConfirmValue::new(
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
        false,                // page_counter
        true,                 // cancel: refusing is never the app's to switch off
        params.offers_more(), // external_menu: how the menu is reached
        footer,
    ));

    // The screen has its own way out, so the extras need not offer one.
    call(&request, params.extras, false, Some(params.br))
}

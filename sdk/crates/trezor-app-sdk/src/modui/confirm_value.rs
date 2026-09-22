//! Confirming a single value.
//!
//! # Example
//!
//! ```no_run
//! use trezor_app_sdk::modui::{self as ui, ConfirmValue, Footer, ValueKind};
//!
//! fn confirm_recipient(address: &str) -> trezor_app_sdk::Result<()> {
//!     ui::confirm_value(ConfirmValue::new(
//!         "Send",
//!         address,
//!         ValueKind::Address,
//!         Some("Recipient"),
//!         None,
//!         Some(Footer::Hint("Check with the source.")),
//!         &[],
//!         true,
//!     ))?
//!     .confirmed()
//! }
//! ```

use super::extra::ExtraItem;
use super::{UiOutcome, call};
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
    /// Something the user should weigh before confirming.
    Warning(&'a str),
}

/// Parameters for [`confirm_value`].
pub struct ConfirmValue<'a> {
    title: &'a str,
    value: &'a str,
    kind: ValueKind,
    subtitle: Option<&'a str>,
    description: Option<&'a str>,
    footer: Option<Footer<'a>>,
    extras: &'a [ExtraItem<'a>],
    cancel: bool,
}

impl<'a> ConfirmValue<'a> {
    /// Confirms one `value` of the given kind under `title`.
    ///
    /// Deliberately one constructor carrying every parameter: the API is meant
    /// to be obvious rather than clever, so there is a single way to build this
    /// and no builders to learn.
    ///
    /// `extras` are labelled pieces the screen can also offer; `cancel` says
    /// whether the block may be abandoned from there. How either is presented
    /// is the library's choice, not the caller's.
    #[allow(clippy::too_many_arguments)]
    pub fn new(
        title: &'a str,
        value: &'a str,
        kind: ValueKind,
        subtitle: Option<&'a str>,
        description: Option<&'a str>,
        footer: Option<Footer<'a>>,
        extras: &'a [ExtraItem<'a>],
        cancel: bool,
    ) -> Self {
        Self {
            title,
            value,
            kind,
            subtitle,
            description,
            footer,
            extras,
            cancel,
        }
    }

    /// Whether the screen has anything to offer besides its main content.
    fn offers_more(&self) -> bool {
        !self.extras.is_empty() || self.cancel
    }
}

// ============================================================================
// Entry point
// ============================================================================

/// Shows one value for confirmation.
pub fn confirm_value(params: ConfirmValue<'_>) -> Result<UiOutcome> {
    let footer = params.footer.map(|f| match f {
        Footer::Hint(text) => (text, false),
        Footer::Warning(text) => (text, true),
    });

    let request = TrezorUiEnum::ConfirmValue(WireConfirmValue::new(
        params.title,
        params.value,
        params.description,
        None, // ButtonRequest: emitted on the trusted side, not from here
        0,
        true, // is_data: values are shown verbatim, not prose
        None, // verb: the label follows the gesture, which the block owns
        params.subtitle,
        false, // info: the menu button is the external one below
        false, // hold: derived from the block
        params.kind == ValueKind::Address,
        false,                // page_counter
        false,                // cancel
        params.offers_more(), // external_menu: how the menu is reached
        footer,
    ));

    call(&request, params.extras, params.cancel)
}

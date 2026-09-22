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
//!         None,
//!     ))?
//!     .confirmed()
//! }
//! ```

use super::details::{self, Details};
use super::{UiOutcome, call_raw};
use crate::Result;
use crate::structs::{ConfirmValue as WireConfirmValue, Property, TrezorUiEnum};

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
    details: Option<Details<'a>>,
}

impl<'a> ConfirmValue<'a> {
    /// Confirms one `value` of the given kind under `title`.
    ///
    /// `details` is an extra page of facts, titled and listed, reachable from
    /// the block's menu.
    pub fn new(
        title: &'a str,
        value: &'a str,
        kind: ValueKind,
        subtitle: Option<&'a str>,
        description: Option<&'a str>,
        footer: Option<Footer<'a>>,
        details: Option<(&'a str, &'a [Property<'a>])>,
    ) -> Self {
        Self {
            title,
            value,
            kind,
            subtitle,
            description,
            footer,
            details,
        }
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

    details::confirm(params.details, || {
        let request = WireConfirmValue::new(
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
            false, // page_counter
            false, // cancel
            true,  // external_menu: how the details menu is reached
            footer,
        );

        call_raw(&TrezorUiEnum::ConfirmValue(request))
    })
}

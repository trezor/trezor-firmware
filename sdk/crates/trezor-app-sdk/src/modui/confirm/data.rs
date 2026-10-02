//! Confirming an opaque byte blob. The public docs live on [`data`].
//!
//! WIP: manual test results with extras and `cancel: true` (testapp):
//! caesar (T3B1) and eckhart (T3W1) draw the menu, the extras and Cancel
//! well, but the way out appears twice — on the screen and again in the menu.
//! The menu's Cancel should only be drawn where the screen has none of its
//! own. bolt (T2T1) draws no menu, so neither the extras nor the asked-for
//! Cancel can be reached.
//!
//! This block exists because of *what* it shows — raw bytes with no meaning
//! the device can interpret, rendered as hex — and not because of how much of
//! it there is. Length is not the caller's problem: a blob of any size is one
//! call returning one outcome, and `internal::data` handles the rest.

use crate::Result;
use crate::modui::{ExtraItem, UiReply, internal};

// ============================================================================
// Data types
// ============================================================================

/// Parameters for [`data`], built by [`Data::new`].
pub struct Data<'a> {
    title: &'a str,
    data: &'a [u8],
    subtitle: Option<&'a str>,
    br: &'a str,
    extras: &'a [ExtraItem<'a>],
    cancel: bool,
}

impl<'a> Data<'a> {
    /// Confirms `data`, shown as hex however long it is.
    ///
    /// - `title` — the heading of every screen.
    /// - `data` — the bytes, of any length.
    /// - `subtitle` — optional line under the heading.
    /// - `br` — the step name the host sees; see
    ///   [step names](crate::modui#step-names).
    /// - `extras` — more the person can look at from this screen; see
    ///   [extras](crate::modui#extras-and-the-way-out).
    /// - `cancel` — whether the extras also offer a way to abandon the block.
    pub fn new(
        title: &'a str,
        data: &'a [u8],
        subtitle: Option<&'a str>,
        br: &'a str,
        extras: &'a [ExtraItem<'a>],
        cancel: bool,
    ) -> Self {
        Self {
            title,
            data,
            subtitle,
            br,
            extras,
            cancel,
        }
    }
}

// ============================================================================
// Entry point
// ============================================================================

/// Asks the person to confirm raw bytes, and waits for the answer.
///
/// For data the device cannot interpret, such as contract call data. The
/// bytes are shown as hex, a screen at a time, and a blob of any length is
/// still one call with one outcome: the app never sees how it was split.
///
/// `Confirmed` means the person went through all of it: there is no way to
/// accept the rest unread.
///
/// # Errors
///
/// See [errors](crate::modui#errors).
///
/// # Example
///
/// ```no_run
/// use trezor_app_sdk::modui::confirm;
///
/// fn confirm_calldata(calldata: &[u8]) -> trezor_app_sdk::Result<()> {
///     confirm::data(confirm::Data::new("Transaction data", calldata, None, "app/data", &[], true))?
///         .confirmed()
/// }
/// ```
pub fn data(params: Data<'_>) -> Result<UiReply> {
    internal::data::confirm(&internal::data::Params {
        title: params.title,
        data: params.data,
        subtitle: params.subtitle,
        br: params.br,
        extras: params.extras,
        cancel: params.cancel,
    })
}

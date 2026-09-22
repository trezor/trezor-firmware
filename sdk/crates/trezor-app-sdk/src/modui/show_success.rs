//! Reporting that something finished.
//!
//! # Example
//!
//! ```no_run
//! use trezor_app_sdk::modui::{self as ui, ShowSuccess};
//!
//! fn signed() -> trezor_app_sdk::Result<()> {
//!     ui::show_success(ShowSuccess::new("Done", "Transaction signed", &[], false))?.confirmed()
//! }
//! ```

use super::extra::ExtraItem;
use super::{UiOutcome, call};
use crate::structs::{ShowSuccess as WireShowSuccess, TrezorUiEnum};
use crate::{Error, Result};

// ============================================================================
// Constants
// ============================================================================

/// How long a success screen stays up before dismissing itself.
const DURATION_MS: u32 = 3200;

// ============================================================================
// Data types
// ============================================================================

/// Parameters for [`show_success`].
pub struct ShowSuccess<'a> {
    title: &'a str,
    content: &'a str,
    extras: &'a [ExtraItem<'a>],
    cancel: bool,
}

impl<'a> ShowSuccess<'a> {
    /// Reports `content` under `title`.
    pub fn new(
        title: &'a str,
        content: &'a str,
        extras: &'a [ExtraItem<'a>],
        cancel: bool,
    ) -> Self {
        Self {
            title,
            content,
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

/// Shows a success screen.
///
/// Note this block says nothing about whether anything was actually signed —
/// it renders what the app gives it, like every other block.
pub fn show_success(params: ShowSuccess<'_>) -> Result<UiOutcome> {
    // This block's wire has no menu button yet, so anything behind one would
    // be silently unreachable. Refusing is worse to use and better to debug.
    if !params.extras.is_empty() {
        return Err(Error::ValueError("extras not yet supported by this block"));
    }
    let request = WireShowSuccess::new(
        params.title,
        params.content,
        "", // button: chrome, follows the block
        Some(DURATION_MS),
        None, // ButtonRequest: emitted on the trusted side, not from here
        0,
    );

    call(
        &TrezorUiEnum::ShowSuccess(request),
        params.extras,
        params.cancel,
    )
}

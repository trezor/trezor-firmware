//! Reporting that something finished.
//!
//! # Example
//!
//! ```no_run
//! use trezor_app_sdk::modui::{self as ui, ShowSuccess};
//!
//! fn signed() -> trezor_app_sdk::Result<()> {
//!     ui::show_success(ShowSuccess::new("Done", "Transaction signed"))?.confirmed()
//! }
//! ```

use super::{UiOutcome, call};
use crate::Result;
use crate::structs::{ShowSuccess as WireShowSuccess, TrezorUiEnum};

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
}

impl<'a> ShowSuccess<'a> {
    /// Reports `content` under `title`.
    pub fn new(title: &'a str, content: &'a str) -> Self {
        Self { title, content }
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
    let request = WireShowSuccess::new(
        params.title,
        params.content,
        "", // button: chrome, follows the block
        Some(DURATION_MS),
        None, // ButtonRequest: emitted on the trusted side, not from here
        0,
    );

    call(&TrezorUiEnum::ShowSuccess(request))
}

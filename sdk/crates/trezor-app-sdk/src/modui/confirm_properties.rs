//! Confirming a list of key/value facts.
//!
//! # Example
//!
//! ```no_run
//! use trezor_app_sdk::modui::{self as ui, ConfirmProperties, Property};
//!
//! fn confirm_stake(amount: &str) -> trezor_app_sdk::Result<()> {
//!     let props = [
//!         Property::new("Amount", amount, false),
//!         Property::new("Resource", "Energy", false),
//!     ];
//!     ui::confirm_properties(ConfirmProperties::new("Summary", &props, None))?.confirmed()
//! }
//! ```

use super::{UiOutcome, call};
use crate::Result;
use crate::structs::{ConfirmProperties as WireConfirmProperties, Property, TrezorUiEnum};

// ============================================================================
// Data types
// ============================================================================

/// Parameters for [`confirm_properties`].
pub struct ConfirmProperties<'a> {
    title: &'a str,
    props: &'a [Property<'a>],
    subtitle: Option<&'a str>,
}

impl<'a> ConfirmProperties<'a> {
    /// Confirms the facts in `props` under `title`.
    pub fn new(title: &'a str, props: &'a [Property<'a>], subtitle: Option<&'a str>) -> Self {
        Self {
            title,
            props,
            subtitle,
        }
    }
}

// ============================================================================
// Entry point
// ============================================================================

/// Shows a list of facts for confirmation.
pub fn confirm_properties(params: ConfirmProperties<'_>) -> Result<UiOutcome> {
    let request = WireConfirmProperties::new(
        params.title,
        params.props,
        params.subtitle,
        None,  // verb: the label follows the gesture, which the block owns
        false, // hold: derived from the block
        None,  // ButtonRequest: emitted on the trusted side, not from here
        0,
    );

    call(&TrezorUiEnum::ConfirmProperties(request))
}

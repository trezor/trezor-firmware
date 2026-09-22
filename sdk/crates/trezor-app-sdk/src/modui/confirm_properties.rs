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
//!     ui::confirm_properties(ConfirmProperties::new("Summary", &props, None, &[], true))?.confirmed()
//! }
//! ```

use super::extra::ExtraItem;
use super::{UiOutcome, call};
use crate::structs::{ConfirmProperties as WireConfirmProperties, Property, TrezorUiEnum};
use crate::{Error, Result};

// ============================================================================
// Data types
// ============================================================================

/// Parameters for [`confirm_properties`].
pub struct ConfirmProperties<'a> {
    title: &'a str,
    props: &'a [Property<'a>],
    subtitle: Option<&'a str>,
    extras: &'a [ExtraItem<'a>],
    cancel: bool,
}

impl<'a> ConfirmProperties<'a> {
    /// Confirms the facts in `props` under `title`.
    pub fn new(
        title: &'a str,
        props: &'a [Property<'a>],
        subtitle: Option<&'a str>,
        extras: &'a [ExtraItem<'a>],
        cancel: bool,
    ) -> Self {
        Self {
            title,
            props,
            subtitle,
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

/// Shows a list of facts for confirmation.
pub fn confirm_properties(params: ConfirmProperties<'_>) -> Result<UiOutcome> {
    // This block's wire has no menu button yet, so anything behind one would
    // be silently unreachable. Refusing is worse to use and better to debug.
    if !params.extras.is_empty() {
        return Err(Error::ValueError("extras not yet supported by this block"));
    }
    let request = WireConfirmProperties::new(
        params.title,
        params.props,
        params.subtitle,
        None,  // verb: the label follows the gesture, which the block owns
        false, // hold: derived from the block
        None,  // ButtonRequest: emitted on the trusted side, not from here
        0,
    );

    call(
        &TrezorUiEnum::ConfirmProperties(request),
        params.extras,
        params.cancel,
    )
}

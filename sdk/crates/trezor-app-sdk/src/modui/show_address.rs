//! Showing an address the user is meant to check.
//!
//! Open question, deliberately left as-is for now: the design calls for this to
//! be decomposed into a value confirmation plus a standalone QR view, so that
//! no block quietly implies core vouched for the address. That needs a QR block
//! the wire cannot express yet, so the composite stands meanwhile.
//!
//! # Example
//!
//! ```no_run
//! use trezor_app_sdk::modui::{self as ui, ShowAddress};
//!
//! fn show_receive(address: &str, path: &str) -> trezor_app_sdk::Result<()> {
//!     ui::show_address(ShowAddress::new(address, None, None, Some(path), &[], false))?.confirmed()
//! }
//! ```

use super::extra::ExtraItem;
use super::{UiOutcome, call};
use crate::structs::{Property, ShowAddress as WireShowAddress, TrezorUiEnum};
use crate::{Error, Result};

// ============================================================================
// Data types
// ============================================================================

/// Parameters for [`show_address`].
pub struct ShowAddress<'a> {
    address: &'a str,
    subtitle: Option<&'a str>,
    account: Option<&'a str>,
    path: Option<&'a str>,
    extras: &'a [ExtraItem<'a>],
    cancel: bool,
}

impl<'a> ShowAddress<'a> {
    /// Shows `address`, with its QR, optionally naming the account it belongs
    /// to and the derivation path it came from.
    pub fn new(
        address: &'a str,
        subtitle: Option<&'a str>,
        account: Option<&'a str>,
        path: Option<&'a str>,
        extras: &'a [ExtraItem<'a>],
        cancel: bool,
    ) -> Self {
        Self {
            address,
            subtitle,
            account,
            path,
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

/// Shows an address for the user to verify.
pub fn show_address(params: ShowAddress<'_>) -> Result<UiOutcome> {
    // This block's wire has no menu button yet, so anything behind one would
    // be silently unreachable. Refusing is worse to use and better to debug.
    if !params.extras.is_empty() {
        return Err(Error::ValueError("extras not yet supported by this block"));
    }
    const NO_XPUBS: &[Property] = &[];

    let request = WireShowAddress::new(
        params.address,
        params.address,
        None, // title: the block's own
        params.subtitle,
        params.account,
        params.path,
        NO_XPUBS,
        true, // addresses are always chunked
        0,    // ButtonRequest code: unused, nothing announces this block
        true, // case matters in an address the user compares by eye
    );

    call(
        &TrezorUiEnum::ShowAddress(request),
        params.extras,
        params.cancel,
    )
}

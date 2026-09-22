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
//!     ui::show_address(ShowAddress::new(address, None, None, Some(path)))?.confirmed()
//! }
//! ```

use super::{UiOutcome, call};
use crate::Result;
use crate::structs::{Property, ShowAddress as WireShowAddress, TrezorUiEnum};

// ============================================================================
// Data types
// ============================================================================

/// Parameters for [`show_address`].
pub struct ShowAddress<'a> {
    address: &'a str,
    subtitle: Option<&'a str>,
    account: Option<&'a str>,
    path: Option<&'a str>,
}

impl<'a> ShowAddress<'a> {
    /// Shows `address`, with its QR, optionally naming the account it belongs
    /// to and the derivation path it came from.
    pub fn new(
        address: &'a str,
        subtitle: Option<&'a str>,
        account: Option<&'a str>,
        path: Option<&'a str>,
    ) -> Self {
        Self {
            address,
            subtitle,
            account,
            path,
        }
    }
}

// ============================================================================
// Entry point
// ============================================================================

/// Shows an address for the user to verify.
pub fn show_address(params: ShowAddress<'_>) -> Result<UiOutcome> {
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

    call(&TrezorUiEnum::ShowAddress(request))
}

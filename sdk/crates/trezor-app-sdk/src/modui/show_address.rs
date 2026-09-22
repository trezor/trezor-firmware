//! Showing an address the person is meant to check. The public docs live on
//! [`show_address`].
//!
//! Open question, deliberately left as-is for now: the design calls for this to
//! be decomposed into a value confirmation plus a standalone QR view, so that
//! no block quietly implies core vouched for the address. That needs a QR block
//! the wire cannot express yet, so the composite stands meanwhile.

use super::extra::ExtraItem;
use super::{BR_CODE_OTHER, UiOutcome, call};
use crate::structs::{Property, ShowAddress as WireShowAddress, TrezorUiEnum};
use crate::{Error, Result};

// ============================================================================
// Data types
// ============================================================================

/// Parameters for [`show_address`], built by [`ShowAddress::new`].
pub struct ShowAddress<'a> {
    address: &'a str,
    subtitle: Option<&'a str>,
    account: Option<&'a str>,
    path: Option<&'a str>,
    br: &'a str,
    extras: &'a [ExtraItem<'a>],
    cancel: bool,
}

impl<'a> ShowAddress<'a> {
    /// Shows `address`, with its QR, optionally naming the account it belongs
    /// to and the derivation path it came from.
    ///
    /// - `address` — the address, shown exactly as given; case matters.
    /// - `subtitle` — optional line under the heading.
    /// - `account` — optional name of the account the address belongs to.
    /// - `path` — optional derivation path, as text.
    /// - `br` — the step name the host sees; see
    ///   [step names](crate::modui#step-names).
    /// - `extras` — more the person can look at from this screen; see
    ///   [extras](crate::modui#extras-and-the-way-out).
    ///   Not shown by this block yet; see [`show_address`].
    /// - `cancel` — whether the extras also offer a way to abandon the block.
    pub fn new(
        address: &'a str,
        subtitle: Option<&'a str>,
        account: Option<&'a str>,
        path: Option<&'a str>,
        br: &'a str,
        extras: &'a [ExtraItem<'a>],
        cancel: bool,
    ) -> Self {
        Self {
            address,
            subtitle,
            account,
            path,
            br,
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

/// Shows an address for the person to check against the host, and waits.
///
/// The address is always shown in chunks and with its QR code. `Confirmed`
/// means the person says it matches.
///
/// # Errors
///
/// This block cannot show extras yet: a non-empty `extras` is refused with
/// [`crate::Error::ValueError`], and `cancel` has no effect. Otherwise see
/// [errors](crate::modui#errors).
///
/// # Example
///
/// ```no_run
/// use trezor_app_sdk::modui::{self as ui, ShowAddress};
///
/// fn show_receive(address: &str, path: &str) -> trezor_app_sdk::Result<()> {
///     ui::show_address(ShowAddress::new(address, None, None, Some(path), "app/address", &[], false))?
///         .confirmed()
/// }
/// ```
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
        true,            // addresses are always chunked
        Some(params.br), // br_name: the step's name; the app owns it (see the field docs)
        BR_CODE_OTHER,   // legacy field; see the constant
        true,            // case matters in an address the person compares by eye
    );

    call(
        &TrezorUiEnum::ShowAddress(request),
        params.extras,
        params.cancel,
        Some(params.br),
    )
}

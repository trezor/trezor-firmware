//! Confirming an opaque byte blob.
//!
//! This block exists because of *what* it shows — raw bytes with no meaning
//! the device can interpret, rendered as hex — and not because of how much of
//! it there is. Length is not the caller's problem: a blob of any size is one
//! call returning one outcome, and [`super::paged`] handles the rest.
//!
//! # Example
//!
//! ```no_run
//! use trezor_app_sdk::modui::{self as ui, ConfirmData};
//!
//! fn confirm_calldata(calldata: &[u8]) -> trezor_app_sdk::Result<()> {
//!     ui::confirm_data(ConfirmData::new("Transaction data", calldata, None))?.confirmed()
//! }
//! ```

use super::paged::{self, BYTES_PER_PAGE, Page, PageCtx};
use super::{UiOutcome, call_raw};
use crate::alloc_types::String;
use crate::structs::{ConfirmWithInfo, StrExt, TrezorUiEnum, TrezorUiResult};
use crate::{Error, Result};

// ============================================================================
// Data types
// ============================================================================

/// Parameters for [`confirm_data`].
pub struct ConfirmData<'a> {
    title: &'a str,
    data: &'a [u8],
    subtitle: Option<&'a str>,
}

impl<'a> ConfirmData<'a> {
    /// Confirms `data`, rendered as hex across as many pages as it takes.
    pub fn new(title: &'a str, data: &'a [u8], subtitle: Option<&'a str>) -> Self {
        Self {
            title,
            data,
            subtitle,
        }
    }
}

// ============================================================================
// Entry point
// ============================================================================

/// Shows an opaque byte blob for confirmation.
pub fn confirm_data(params: ConfirmData<'_>) -> Result<UiOutcome> {
    // One buffer reused for every page rather than an allocation per page.
    let mut hex = String::with_capacity(BYTES_PER_PAGE * 2);

    paged::confirm_in_pages(params.data.len().div_ceil(BYTES_PER_PAGE), |ctx| {
        let start = ctx.index * BYTES_PER_PAGE;
        let end = (start + BYTES_PER_PAGE).min(params.data.len());

        encode_hex(&params.data[start..end], &mut hex);
        show_page(&params, &hex, &ctx)
    })
}

// ============================================================================
// Internals
// ============================================================================

/// Renders one page and waits for the user.
fn show_page(params: &ConfirmData<'_>, hex: &str, ctx: &PageCtx) -> Result<Page> {
    let items = [StrExt::mono(hex)];

    let request = ConfirmWithInfo::new(
        params.title,
        params.subtitle,
        &items,
        ctx.verb(),
        ctx.verb_skip(),
        None, // ButtonRequest: emitted on the trusted side, not from here
        0,
    );

    match call_raw(&TrezorUiEnum::ConfirmWithInfo(request))? {
        TrezorUiResult::Confirmed => Ok(Page::Advance),
        TrezorUiResult::Info => Ok(Page::ConfirmAll),
        TrezorUiResult::Cancelled => Ok(Page::Cancelled),
        TrezorUiResult::Back | TrezorUiResult::Integer(_) => Err(Error::InvalidMessage),
    }
}

/// Writes `bytes` as lowercase hex into `out`, replacing its contents.
fn encode_hex(bytes: &[u8], out: &mut String) {
    const DIGITS: &[u8; 16] = b"0123456789abcdef";

    out.clear();
    for byte in bytes {
        out.push(DIGITS[(byte >> 4) as usize] as char);
        out.push(DIGITS[(byte & 0x0f) as usize] as char);
    }
}

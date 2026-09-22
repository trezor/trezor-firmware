//! Confirming an opaque byte blob. The public docs live on [`confirm_data`].
//!
//! This block exists because of *what* it shows — raw bytes with no meaning
//! the device can interpret, rendered as hex — and not because of how much of
//! it there is. Length is not the caller's problem: a blob of any size is one
//! call returning one outcome, and `paged` handles the rest.

use super::extra::ExtraItem;
use super::paged::{self, BYTES_PER_PAGE, Page, PageCtx};
use super::screen::Screen;
use super::{BR_CODE_OTHER, UiOutcome, menu};
use crate::alloc_types::String;
use crate::structs::{ConfirmWithInfo, StrExt, TrezorUiEnum, UiReply};
use crate::{Error, Result};

// ============================================================================
// Data types
// ============================================================================

/// Parameters for [`confirm_data`], built by [`ConfirmData::new`].
pub struct ConfirmData<'a> {
    title: &'a str,
    data: &'a [u8],
    subtitle: Option<&'a str>,
    br: &'a str,
    extras: &'a [ExtraItem<'a>],
    cancel: bool,
}

impl<'a> ConfirmData<'a> {
    /// Confirms `data`, rendered as hex across as many pages as it takes.
    ///
    /// - `title` — the heading of every page.
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

    /// Whether the screen has anything to offer besides its main content.
    fn offers_more(&self) -> bool {
        !self.extras.is_empty() || self.cancel
    }
}

// ============================================================================
// Entry point
// ============================================================================

/// Asks the person to confirm raw bytes, and waits for the answer.
///
/// For data the device cannot interpret, such as contract call data. The
/// bytes are shown as hex, one page at a time, and a blob of any length is
/// still one call with one outcome: the app never sees the pages.
///
/// The person can accept the pages they have not reached yet without reading
/// them, and that is still `Confirmed`. Use this block only where skipping the
/// rest is acceptable; anything the person must read belongs in a block that
/// shows it whole.
///
/// # Errors
///
/// See [errors](crate::modui#errors).
///
/// # Example
///
/// ```no_run
/// use trezor_app_sdk::modui::{self as ui, ConfirmData};
///
/// fn confirm_calldata(calldata: &[u8]) -> trezor_app_sdk::Result<()> {
///     ui::confirm_data(ConfirmData::new("Transaction data", calldata, None, "app/data", &[], true))?
///         .confirmed()
/// }
/// ```
pub fn confirm_data(params: ConfirmData<'_>) -> Result<UiOutcome> {
    // This block drives its own screens, so it makes the check `call` makes for
    // every other one: a step with no identity is worse for the host than a
    // block that deliberately announces nothing.
    if params.br.is_empty() {
        return Err(Error::ValueError("a step name must not be empty"));
    }

    // One buffer reused for every page rather than an allocation per page.
    let mut hex = String::with_capacity(BYTES_PER_PAGE * 2);
    // One screen for the whole sequence: each page rebuilds it, because its
    // content changed, but a trip through the extras and back does not.
    let screen = Screen::new();

    paged::confirm_in_pages(params.data.len().div_ceil(BYTES_PER_PAGE), |ctx| {
        let start = ctx.index * BYTES_PER_PAGE;
        let end = (start + BYTES_PER_PAGE).min(params.data.len());

        encode_hex(&params.data[start..end], &mut hex);
        show_page(&params, &hex, &ctx, &screen)
    })
}

// ============================================================================
// Internals
// ============================================================================

/// Renders one page and waits for the person, showing the same page until
/// they leave it.
fn show_page(params: &ConfirmData<'_>, hex: &str, ctx: &PageCtx, screen: &Screen) -> Result<Page> {
    let items = [StrExt::mono(hex)];

    let request = TrezorUiEnum::ConfirmWithInfo(ConfirmWithInfo::new(
        params.title,
        params.subtitle,
        &items,
        // Button words, which this library has no business choosing. What it
        // knows is semantic — this is page `ctx.index`, there are more or there
        // are not, and the screen has extras or it does not — and the trusted
        // side should turn that into buttons in the person's own language. The
        // wire has no field for any of it, only for the labels themselves, so
        // they are written here, in English, at the one point that cannot
        // avoid them. They go the moment the wire carries the facts instead.
        if ctx.is_last { "Continue" } else { "Show next" },
        match (params.offers_more(), ctx.is_last) {
            (true, _) => Some("Menu"),
            (false, false) => Some("Confirm all"),
            (false, true) => None,
        },
        Some(params.br), // br_name: the step's name; the app owns it (see the field docs)
        BR_CODE_OTHER,   // legacy field; see the constant
    ));

    // This page's content is new, so the screen is built rather than reopened.
    let mut reply = screen.show(&request)?;

    loop {
        match reply {
            // What "next page" will be once core can tell it is at the edge
            // of the window it was given. Nothing sends it yet.
            UiReply::Forward => return Ok(Page::Advance),
            UiReply::Backward => return Ok(Page::Retreat),
            // How "next page" arrives today, and the reason the two words in
            // the request above have to exist: this also means "done" on the
            // last page, and only `ctx` tells them apart.
            UiReply::Confirmed => return Ok(Page::Advance),
            UiReply::ConfirmedAll => return Ok(Page::ConfirmAll),
            // The extras, which is all this should ever mean.
            UiReply::WantsMore if params.offers_more() => {
                match menu::open(params.extras, params.cancel, Some(params.br))? {
                    Some(outcome) => return Ok(Page::Decided(outcome)),
                    // Back to the page the person was reading, as they left it.
                    None => reply = screen.reshow(&request)?,
                }
            }
            // Scaffolding, and the second half of the overload `ConfirmedAll`
            // exists to end: a paged screen has one secondary button, so when
            // there are no extras this library makes it the skip-ahead and
            // core has no way to say so.
            UiReply::WantsMore => return Ok(Page::ConfirmAll),
            UiReply::Cancelled => return Ok(Page::Cancelled),
            _ => return Err(Error::InvalidMessage),
        }
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

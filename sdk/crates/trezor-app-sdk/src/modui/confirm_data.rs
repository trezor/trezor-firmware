//! Confirming an opaque byte blob. The public docs live on [`confirm_data`].
//!
//! This block exists because of *what* it shows — raw bytes with no meaning
//! the device can interpret, rendered as hex — and not because of how much of
//! it there is. Length is not the caller's problem: a blob of any size is one
//! call returning one outcome, and `chunked` handles the rest.

use super::chunked::{self, AfterChunk, BYTES_PER_CHUNK};
use super::extra::ExtraItem;
use super::screen::Screen;
use super::{BR_CODE_OTHER, UiOutcome, menu};
use crate::alloc_types::String;
use crate::structs::{ConfirmValue as WireConfirmValue, TrezorUiEnum, UiReply};
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
    menu::check_extras(params.extras, params.cancel)?;

    // One buffer reused for every chunk rather than an allocation per chunk.
    let mut hex = String::with_capacity(BYTES_PER_CHUNK * 2);
    // One screen for the whole sequence: each chunk rebuilds it, because its
    // content changed, but a trip through the extras and back does not.
    let screen = Screen::new();

    chunked::confirm_in_chunks(params.data.len().div_ceil(BYTES_PER_CHUNK), |ctx| {
        let start = ctx.index * BYTES_PER_CHUNK;
        let end = (start + BYTES_PER_CHUNK).min(params.data.len());

        encode_hex(&params.data[start..end], &mut hex);
        show_chunk(&params, &hex, &screen)
    })
}

// ============================================================================
// Internals
// ============================================================================

/// Sends one chunk and waits for the person, showing the same chunk until
/// they leave it.
///
/// A chunk goes as a value, the screen every model pages: core splits it across
/// as many screens as it takes, and the person answers only once they have
/// seen all of it.
fn show_chunk(params: &ConfirmData<'_>, hex: &str, screen: &Screen) -> Result<AfterChunk> {
    let request = TrezorUiEnum::ConfirmValue(WireConfirmValue::new(
        params.title,
        hex,
        None,            // description
        Some(params.br), // br_name: the step's name; the app owns it
        BR_CODE_OTHER,   // legacy field; see the constant
        true,            // is_data: raw data, shown verbatim
        None,            // verb: the model's own
        params.subtitle,
        false,                // info: the menu button is the external one below
        false,                // hold
        false,                // chunkify: hex, not an address to compare by eye
        true,                 // page_counter: where the person is within the chunk
        true,                 // cancel: the screen's own way out
        params.offers_more(), // external_menu: how the extras are reached
        None,                 // footer
    ));

    // This chunk's content is new, so the screen is built rather than reopened.
    let mut reply = screen.show(&request)?;

    loop {
        match reply {
            // What "next chunk" will be once core can tell it has paged to the
            // edge of the chunk it was given. Nothing sends it yet.
            UiReply::Forward => return Ok(AfterChunk::Advance),
            UiReply::Backward => return Ok(AfterChunk::Retreat),
            // Core pages within the chunk, so a yes means the person has seen
            // all of it. Whether that finishes the block is the loop's to say.
            UiReply::Confirmed => return Ok(AfterChunk::Advance),
            UiReply::ConfirmedAll => return Ok(AfterChunk::ConfirmAll),
            // The extras, which is all this can mean: the screen has no other
            // secondary button.
            UiReply::WantsMore if params.offers_more() => {
                match menu::open(params.extras, params.cancel, Some(params.br))? {
                    Some(outcome) => return Ok(AfterChunk::Decided(outcome)),
                    // Back to the chunk the person was reading, as they left it.
                    None => reply = screen.reshow(&request)?,
                }
            }
            UiReply::Cancelled => return Ok(AfterChunk::Cancelled),
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

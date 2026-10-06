//! How [`confirm::data`](crate::modui::confirm::data) shows a blob: in chunks,
//! each a value screen that core pages, with the extras menu between them.

use super::chunked::{self, AfterChunk, BYTES_PER_CHUNK};
use super::transport::LayoutHandle;
use super::{BR_CODE_OTHER, menu};
use crate::alloc_types::String;
use crate::modui::ExtraItem;
use crate::traits::ui::{ConfirmValue as WireConfirmValue, UiReply};
use crate::{Error, Result};

/// What the block was given, as [`confirm::Data`](crate::modui::confirm::Data)
/// holds it.
pub(in crate::modui) struct Params<'a> {
    pub title: &'a str,
    pub data: &'a [u8],
    pub subtitle: Option<&'a str>,
    pub br: &'a str,
    pub extras: &'a [ExtraItem<'a>],
}

/// Runs the block.
pub(in crate::modui) fn confirm(params: &Params<'_>) -> Result<UiReply> {
    // This block drives its own screens, so it makes the check `call` makes for
    // every other one: a step with no identity is worse for the host than a
    // block that deliberately announces nothing.
    if params.br.is_empty() {
        return Err(Error::ValueError("a step name must not be empty"));
    }
    menu::check_extras(params.extras)?;

    // One buffer reused for every chunk rather than an allocation per chunk.
    let mut hex = String::with_capacity(BYTES_PER_CHUNK * 2);
    // One layout for the whole sequence: each chunk rebuilds it, because its
    // content changed, but a trip through the extras and back does not.
    let layout = LayoutHandle::new();

    chunked::confirm_in_chunks(params.data.len().div_ceil(BYTES_PER_CHUNK), |ctx| {
        let start = ctx.index * BYTES_PER_CHUNK;
        let end = (start + BYTES_PER_CHUNK).min(params.data.len());

        encode_hex(&params.data[start..end], &mut hex);
        show_chunk(params, &hex, &layout)
    })
}

/// Sends one chunk and waits for the person, showing the same chunk until
/// they leave it.
///
/// A chunk goes as a value, the screen every model pages: core splits it across
/// as many screens as it takes, and the person answers only once they have
/// seen all of it.
fn show_chunk(params: &Params<'_>, hex: &str, layout: &LayoutHandle) -> Result<AfterChunk> {
    // The screen has a menu exactly when the app offered extras.
    let has_menu = !params.extras.is_empty();
    let request = WireConfirmValue::new(
        params.title,
        hex,
        None,            // description
        Some(params.br), // br_name: the step's name; the app owns it
        BR_CODE_OTHER,   // legacy field; see the constant
        true,            // is_data: raw data, shown verbatim
        None,            // verb: the model's own
        params.subtitle,
        false,    // info: the menu button is the external one below
        false,    // hold
        false,    // chunkify: hex, not an address to compare by eye
        true,     // page_counter: where the person is within the chunk
        has_menu, // external_menu: how the extras are reached
        None,     // footer
    );

    // This chunk's content is new, so the layout is built rather than reopened.
    let mut reply = layout.show(&request)?;

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
            // The menu: the extras, and whatever way out the model keeps there.
            UiReply::WantsMore => {
                match menu::open(params.extras, Some(params.br))? {
                    Some(reply) => return Ok(AfterChunk::Decided(reply)),
                    // Back to the chunk the person was reading, as they left it.
                    None => reply = layout.reshow(&request)?,
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

//! How [`confirm::data`](crate::modui::confirm::data) shows a blob: in chunks,
//! each a value screen that core pages, and whose menu core runs.

use super::chunked::{self, AfterChunk, BYTES_PER_CHUNK};
use crate::alloc_types::String;
use crate::app_runtime2::get_ui_or_die;
use crate::modui::confirm::Data;
use crate::structs::{Commitment, ConfirmValue, OptStrSlice, ValueKind};
use crate::traits::ui::{UiReply, UiV1Dyn as _};
use crate::{IntoAppResult, Result};

/// Runs the block.
pub(in crate::modui) fn confirm(params: &Data<'_>) -> Result<UiReply> {
    // One buffer reused for every chunk rather than an allocation per chunk.
    let mut hex = String::with_capacity(BYTES_PER_CHUNK * 2);

    chunked::confirm_in_chunks(params.data.len().div_ceil(BYTES_PER_CHUNK), |ctx| {
        let start = ctx.index * BYTES_PER_CHUNK;
        let end = (start + BYTES_PER_CHUNK).min(params.data.len());

        encode_hex(&params.data[start..end], &mut hex);
        show_chunk(params, &hex)
    })
}

/// Sends one chunk and waits for the person to decide it.
///
/// A chunk goes as a value, the screen every model pages: core splits it across
/// as many screens as it takes, and runs the chunk's menu itself. The person
/// answers only once they have seen all of it.
fn show_chunk(params: &Data<'_>, hex: &str) -> Result<AfterChunk> {
    let request = ConfirmValue {
        title: params.title.into(),
        value: hex.into(),
        kind: ValueKind::Data,
        subtitle: params.subtitle.into(),
        description: OptStrSlice::NONE,
        footer: OptStrSlice::NONE,
        footer_warning: false,
        commitment: Commitment::Step,
        br_name: params.br.into(),
        extras: params.extras.into(),
    };

    Ok(
        match get_ui_or_die().confirm_value(request).into_app_result()? {
            // Core pages within the chunk, so a yes means the person has seen all
            // of it. Whether that finishes the block is the loop's to say.
            UiReply::Confirmed => AfterChunk::Advance,
            UiReply::Cancelled => AfterChunk::Cancelled,
            // WIP: chunk paging (`Forward`, `Backward`, `ConfirmedAll`) comes back
            // here when it lands; see `UiReply`.
        },
    )
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

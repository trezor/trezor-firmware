//! Content too long to send to core in one request.
//!
//! Two different things split long content, and this module is only one of
//! them:
//!
//! - **Chunking** — this library cuts the app's data into chunks and sends
//!   each chunk as its own request, because a request has to fit in one IPC
//!   message. That is this module.
//! - **Paging** — core splits one chunk across as many screens as it takes,
//!   because a screen holds far less than a message. That is the renderer's,
//!   happens inside a single request, and this library never sees it.
//!
//! Today the two meet only at a chunk's edge: each chunk is shown on its own,
//! core pages within it, and the person's yes on its last page moves to the
//! next chunk.
//!
//! WIP, the direction: join the two into one continuous read, as the module
//! docs lay out. [`UiReply::Forward`] and [`UiReply::Backward`] are reserved
//! for it.
//!
//! Chunking is an implementation detail of this crate, never an API choice. A
//! modular app never picks a "chunked" block, never sets a chunk size, and
//! never learns how many chunks there were or which button ended the sequence:
//! it hands over a value and gets one outcome.
//!
//! Every block whose content can be arbitrarily long routes through here, so
//! the behaviour is identical wherever it appears and no single block becomes
//! "the chunked one".
//!
//! # Example
//!
//! ```text
//! // A block supplies only "show chunk N"; the loop belongs here:
//! chunked::confirm_in_chunks(chunk_count, |ctx| {
//!     let slice = chunk_of(data, ctx.index);
//!     show_chunk(&params, slice, &ctx)
//! })
//! ```

use super::UiReply;
use crate::Result;

// ============================================================================
// Constants
// ============================================================================

/// Bytes of raw data sent to core per chunk.
///
/// A whole request has to fit in one IPC message, and hex takes two characters
/// a byte, so a chunk is under half a message, leaving the rest for the other
/// fields of the request. Core pages each chunk itself.
pub(super) const BYTES_PER_CHUNK: usize = (MAX_REQUEST_BYTES - REQUEST_OVERHEAD) / 2;

/// The largest request core is asked to hold at once.
const MAX_REQUEST_BYTES: usize = 1024;

/// Room kept in a request for everything but the chunk: title, subtitle, step
/// name, and the encoding around them.
const REQUEST_OVERHEAD: usize = 256;

// ============================================================================
// Data types
// ============================================================================

/// What should happen after one chunk was shown.
///
/// # Who uses this
///
/// - **Written by a block**, in the closure it hands to
///   [`confirm_in_chunks`]. The block
///   turns a [`UiReply`] into this, adding what the reply cannot say: what came
///   of a trip through the extras.
/// - **Read by [`confirm_in_chunks`]**, which owns the index and decides what
///   to send next.
/// - **Never crosses IPC, and never reaches an app.** The reply an app gets
///   carries no notion of chunks, which is the whole point: an app cannot
///   learn that its value was shown in more than one piece.
pub(super) enum AfterChunk {
    /// Move to the next chunk, or finish if this was the last.
    Advance,
    /// Go back to the chunk before, or stay put if this was the first.
    ///
    /// WIP: nothing produces this yet. Core cannot tell it has paged back to
    /// the start of the chunk it was given, so no screen offers the gesture —
    /// see the note where core turns a layout's result into a reply. The loop
    /// handles it so that the day it can, only the block changes.
    Retreat,
    /// Accept the remainder without reading it.
    ///
    /// WIP: nothing produces this yet. No screen offers a skip-ahead, and
    /// whether one should is a decision still to be made; the loop handles it
    /// so that making it changes only the block.
    ConfirmAll,
    /// Something ended the block outright, such as a menu entry.
    Decided(UiReply),
    Cancelled,
}

/// Where the person is in the sequence, and the chrome that follows from it.
pub(super) struct ChunkCtx {
    /// Zero-based chunk index, used to slice the content.
    pub index: usize,
    pub is_last: bool,
}

// ============================================================================
// Entry point
// ============================================================================

/// Shows up to `chunk_count` chunks in order, stopping as soon as the person decides.
///
/// `show` sends one chunk and reports what the person did with it.
pub(super) fn confirm_in_chunks<F>(chunk_count: usize, mut show: F) -> Result<UiReply>
where
    F: FnMut(ChunkCtx) -> Result<AfterChunk>,
{
    // Empty content still gets one screen, or the person confirms nothing.
    let chunk_count = chunk_count.max(1);
    let mut index = 0;

    // Every way out of this loop is a `return` beside the reason for it, and
    // the loop itself cannot end. That is deliberate: a confirmation must
    // never be what a loop yields by running out. `break` here, or a
    // trailing `Ok(Confirmed)` below, would mean an edit that changed how the
    // loop finishes could turn into a silent yes on a signing device.
    loop {
        let is_last = index + 1 == chunk_count;

        match show(ChunkCtx { index, is_last })? {
            // Accepting the last chunk is the only way to a yes by reading.
            AfterChunk::Advance if is_last => return Ok(UiReply::Confirmed),
            AfterChunk::Advance => index += 1,
            // Already at the start: there is nowhere to go, so show it again.
            AfterChunk::Retreat => index = index.saturating_sub(1),
            // And this is the only way to a yes without reading — passed on
            // as what it is rather than folded into a plain yes.
            AfterChunk::ConfirmAll => return Ok(UiReply::ConfirmedAll),
            AfterChunk::Decided(reply) => return Ok(reply),
            AfterChunk::Cancelled => return Ok(UiReply::Cancelled),
        }
    }
}

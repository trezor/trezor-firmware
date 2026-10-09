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
//! docs lay out. The paging replies (`UiReply::Forward`, `Backward`,
//! `ConfirmedAll`) are commented out until then.
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

use crate::Result;
use crate::traits::ui::UiReply;

// ============================================================================
// Constants
// ============================================================================

/// Bytes of raw data sent to core per chunk.
///
/// Chunking bounds how much of a long blob core holds at once: core keeps
/// several copies of a request while it draws it, and hex doubles the data.
/// Core's inbox for app messages (32 KB) is the hard ceiling, far above this.
/// Core pages each chunk itself.
///
/// WIP: a guess. Measure core's heap with a large blob and raise it.
pub(in crate::modui) const BYTES_PER_CHUNK: usize = 384;

// ============================================================================
// Data types
// ============================================================================

/// What should happen after one chunk was shown.
///
/// # Who uses this
///
/// - **Written by a block**, in the closure it hands to
///   [`confirm_in_chunks`], from the chunk's [`UiReply`].
/// - **Read by [`confirm_in_chunks`]**, which owns the index and decides what
///   to send next.
/// - **Never crosses IPC, and never reaches an app.** The reply an app gets
///   carries no notion of chunks, which is the whole point: an app cannot
///   learn that its value was shown in more than one piece.
pub(in crate::modui) enum AfterChunk {
    /// Move to the next chunk, or finish if this was the last.
    Advance,
    // WIP: chunk paging; these come back with it (see `UiReply`).
    // /// Go back to the chunk before, or stay put if this was the first.
    // Retreat,
    // /// Accept the remainder without reading it.
    // ConfirmAll,
    Cancelled,
}

/// Where the person is in the sequence, and the chrome that follows from it.
pub(in crate::modui) struct ChunkCtx {
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
pub(in crate::modui) fn confirm_in_chunks<F>(chunk_count: usize, mut show: F) -> Result<UiReply>
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
            // WIP: chunk paging (see `AfterChunk`).
            // AfterChunk::Retreat => index = index.saturating_sub(1),
            // AfterChunk::ConfirmAll => return Ok(UiReply::ConfirmedAll),
            AfterChunk::Cancelled => return Ok(UiReply::Cancelled),
        }
    }
}

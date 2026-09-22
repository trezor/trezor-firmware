//! Content that may not fit on one screen.
//!
//! Paging is an implementation detail of this crate, never an API choice. A
//! modular app never picks a "paged" block, never sets a page size, and never
//! learns how many pages there were or which button ended the sequence: it
//! hands over a value and gets one outcome.
//!
//! Every block whose content can be arbitrarily long routes through here, so
//! the behaviour is identical wherever it appears and no single block becomes
//! "the paged one".
//!
//! # Example
//!
//! ```text
//! // A block supplies only "render page N"; the loop belongs here:
//! paged::confirm_in_pages(page_count, |ctx| {
//!     let slice = page_of(data, ctx.index);
//!     show_page(&params, slice, &ctx)
//! })
//! ```

use super::UiOutcome;
use crate::Result;
#[cfg(doc)]
use crate::structs::UiReply;

// ============================================================================
// Constants
// ============================================================================

/// Bytes of raw data rendered per page.
///
/// This sits on the wrong side of the boundary: the renderer knows what fits,
/// the SDK only guesses. It is kept here once rather than in every app that
/// shows a blob — today each app hardcodes its own copy. The fix is for the
/// renderer to report how much it actually consumed.
pub(super) const BYTES_PER_PAGE: usize = 81; // 9 rows of 18 hex digits

// ============================================================================
// Data types
// ============================================================================

/// What should happen after one page was shown.
///
/// # Who uses this
///
/// - **Written by a block**, in the closure it hands to
///   [`confirm_in_pages`]. The block
///   turns a [`UiReply`] into this, adding what the reply cannot say: whether
///   a screen with no extras meant the skip-ahead, and what came of a trip
///   through the extras.
/// - **Read by [`confirm_in_pages`]**, which owns the index and decides what
///   to send next.
/// - **Never crosses IPC, and never reaches an app.** The public
///   [`UiOutcome`] has no notion of pages, which is the whole point: an app
///   cannot learn that its value was shown in more than one piece.
pub(super) enum Page {
    /// Move to the next page, or finish if this was the last.
    Advance,
    /// Go back to the page before, or stay put if this was the first.
    ///
    /// WIP: nothing produces this yet. Core cannot tell it is at the start of
    /// what it was given, so no screen offers the gesture — see the note in
    /// `send_ui_result`. The loop handles it so that the day it can, only the
    /// block changes.
    Retreat,
    /// Accept the remainder without reading it.
    ConfirmAll,
    /// Something ended the block outright, such as a menu entry.
    Decided(UiOutcome),
    Cancelled,
}

/// Where the person is in the sequence, and the chrome that follows from it.
pub(super) struct PageCtx {
    /// Zero-based page index, used to slice the content.
    pub index: usize,
    pub is_last: bool,
}

// ============================================================================
// Entry point
// ============================================================================

/// Shows up to `page_count` pages in order, stopping as soon as the person decides.
///
/// `show` renders one page and reports what the person did with it.
pub(super) fn confirm_in_pages<F>(page_count: usize, mut show: F) -> Result<UiOutcome>
where
    F: FnMut(PageCtx) -> Result<Page>,
{
    // Empty content still gets one screen, or the person confirms nothing.
    let page_count = page_count.max(1);
    let mut index = 0;

    // Every way out of this loop is a `return` beside the reason for it, and
    // the loop itself cannot end. That is deliberate: a confirmation must
    // never be what a loop yields by running out. `break` here, or a
    // trailing `Ok(Confirmed)` below, would mean an edit that changed how the
    // loop finishes could turn into a silent yes on a signing device.
    loop {
        let is_last = index + 1 == page_count;

        match show(PageCtx { index, is_last })? {
            // Accepting the last page is the only way to a yes by reading.
            Page::Advance if is_last => return Ok(UiOutcome::Confirmed),
            Page::Advance => index += 1,
            // Already at the start: there is nowhere to go, so show it again.
            Page::Retreat => index = index.saturating_sub(1),
            // And this is the only way to a yes without reading — which is
            // why it is its own variant rather than an early exit.
            Page::ConfirmAll => return Ok(UiOutcome::Confirmed),
            Page::Decided(outcome) => return Ok(outcome),
            Page::Cancelled => return Ok(UiOutcome::Cancelled),
        }
    }
}

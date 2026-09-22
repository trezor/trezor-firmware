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
//!     show_page(&params, slice, &ctx) // uses ctx.verb(), ctx.verb_skip()
//! })
//! ```

use super::UiOutcome;
use crate::Result;

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

/// What the user chose on a single page.
///
/// Private on purpose: the public outcome has no notion of pages, so this
/// never escapes the crate.
pub(super) enum Page {
    /// Move to the next page, or finish if this was the last.
    Advance,
    /// Accept the remainder without reading it.
    ConfirmAll,
    Cancelled,
}

/// Where the user is in the sequence, and the chrome that follows from it.
pub(super) struct PageCtx {
    /// Zero-based page index, used to slice the content.
    pub index: usize,
    pub is_last: bool,
}

impl PageCtx {
    /// Main button: advances, or completes the block on the last page.
    pub fn verb(&self) -> &'static str {
        if self.is_last {
            "Continue"
        } else {
            "Show next"
        }
    }

    /// Shortcut past the remaining pages; meaningless on the last one.
    pub fn verb_skip(&self) -> Option<&'static str> {
        if self.is_last {
            None
        } else {
            Some("Confirm all")
        }
    }
}

// ============================================================================
// Entry point
// ============================================================================

/// Shows up to `page_count` pages in order, stopping as soon as the user decides.
///
/// `show` renders one page and reports what the user did with it.
pub(super) fn confirm_in_pages<F>(page_count: usize, mut show: F) -> Result<UiOutcome>
where
    F: FnMut(PageCtx) -> Result<Page>,
{
    // Empty content still gets one screen, or the user confirms nothing.
    let page_count = page_count.max(1);

    for index in 0..page_count {
        let is_last = index + 1 == page_count;
        let ctx = PageCtx { index, is_last };

        match show(ctx)? {
            Page::Advance if is_last => break,
            Page::Advance => (),
            Page::ConfirmAll => break,
            Page::Cancelled => return Ok(UiOutcome::Cancelled),
        }
    }

    Ok(UiOutcome::Confirmed)
}

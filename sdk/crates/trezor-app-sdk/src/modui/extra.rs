//! Extra data a screen can offer beyond the thing it is confirming.
//!
//! A block takes a list of labelled extras. Each one says *how its content is
//! obtained* — already in hand, or fetched on demand — and nothing about how it
//! should look. Whether the library shows them as a menu, as extra pages, or
//! folds them into the screen is not the app's concern, and deliberately not
//! expressible from here.
//!
//! That is the whole vocabulary: no menus, no trees, no callbacks deciding
//! outcomes. An app lists what it has and gets one answer back.
//!
//! # Example
//!
//! ```no_run
//! use trezor_app_sdk::modui::{ExtraItem, Property};
//!
//! fn account_extras<'a>(props: &'a [Property<'a>]) -> [ExtraItem<'a>; 1] {
//!     [ExtraItem::simple("Account info", props)]
//! }
//! ```

use crate::structs::Property;

// ============================================================================
// Data types
// ============================================================================

/// How a piece of extra data supplies what it shows.
///
/// The variants differ only in where the content comes from. Adding a kind
/// means adding a variant here, and every block gains it at once.
pub enum Extra<'a> {
    /// Content the app already holds.
    Simple(&'a [Property<'a>]),

    /// Content fetched on demand, so it need never be held whole.
    ///
    /// Called with a byte offset and a buffer to fill; returns how many bytes
    /// were written, where fewer than the buffer's length means the end has
    /// been reached.
    ///
    /// This closure is Rust-side only and never crosses IPC — it is called by
    /// the library, in the app's own address space. **Provisional**: how paging
    /// should work is still an open question, and this signature is the
    /// starting point for exploring it rather than a settled answer.
    Paginated(&'a dyn Fn(usize, &mut [u8]) -> usize),
    //
    // Other kinds belong here as they are needed, each differing only in how it
    // obtains what it shows — a QR rendering of a string, for instance.
    // Deliberately absent until something asks for one.
}

/// One labelled piece of extra data.
pub struct ExtraItem<'a> {
    pub(super) label: &'a str,
    pub(super) value: Extra<'a>,
}

impl<'a> ExtraItem<'a> {
    /// An extra of the given kind, named by `label`.
    pub fn new(label: &'a str, value: Extra<'a>) -> Self {
        Self { label, value }
    }

    /// The common case: facts the app already has.
    pub fn simple(label: &'a str, props: &'a [Property<'a>]) -> Self {
        Self::new(label, Extra::Simple(props))
    }
}

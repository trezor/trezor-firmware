//! Extra data a screen can offer beyond the thing it is confirming. The public
//! docs live on [`ExtraItem`].
//!
//! Each extra says how its content is obtained, and nothing about how it looks.
//! That is the whole vocabulary: no menus, no trees, no callbacks deciding
//! outcomes.

use crate::structs::Property;

// ============================================================================
// Data types
// ============================================================================

/// Where a piece of extra data comes from.
///
/// The variants differ only in how the content is obtained, never in how it
/// looks. Most apps only need [`ExtraItem::simple`].
pub enum Extra<'a> {
    /// Content the app already holds.
    Simple(&'a [Property<'a>]),

    /// Content fetched on demand, a chunk at a time, so it need never be held
    /// whole. Core pages each chunk on its own.
    ///
    /// Called with a byte offset and a buffer to fill; returns how many bytes
    /// were written, where fewer than the buffer's length means the end has
    /// been reached.
    ///
    /// The closure runs inside the app and never crosses IPC.
    ///
    /// **Not implemented yet**: a block given one returns
    /// [`crate::Error::ValueError`] as soon as it is called, before anything is
    /// shown. The signature is provisional and may change.
    Chunked(&'a dyn Fn(usize, &mut [u8]) -> usize),
    //
    // Other kinds belong here as they are needed, each differing only in how it
    // obtains what it shows — a QR rendering of a string, for instance.
    // Deliberately absent until something asks for one.
}

/// One labelled piece of extra data, offered by a block's screen.
///
/// The label is what the person picks it by; the content is shown when they
/// do, and the block comes back as they left it when they are done. How the
/// extras are presented is the library's choice. See
/// [extras](crate::modui#extras-and-the-way-out).
///
/// # Example
///
/// ```no_run
/// use trezor_app_sdk::modui::{ExtraItem, Property};
///
/// fn account_extras<'a>(props: &'a [Property<'a>]) -> [ExtraItem<'a>; 1] {
///     [ExtraItem::simple("Account info", props)]
/// }
/// ```
pub struct ExtraItem<'a> {
    pub(super) label: &'a str,
    pub(super) value: Extra<'a>,
}

impl<'a> ExtraItem<'a> {
    /// An extra labelled `label`, whose content comes from `value`.
    pub fn new(label: &'a str, value: Extra<'a>) -> Self {
        Self { label, value }
    }

    /// The common case: key/value facts the app already has, labelled `label`.
    pub fn simple(label: &'a str, props: &'a [Property<'a>]) -> Self {
        Self::new(label, Extra::Simple(props))
    }
}

//! Extra data a screen can offer beyond the thing it is confirming. The public
//! docs live on [`ExtraItem`].
//!
//! Each extra is a label and the facts behind it, and nothing about how it
//! looks. That is the whole vocabulary: no menus, no trees, no callbacks
//! deciding outcomes.

/// One labelled piece of extra data, offered by a block's screen.
///
/// The label is what the person picks it by; the facts are shown when they
/// do, and the block comes back as they left it when they are done. The extras
/// travel with the block's request, and core presents them. See
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
pub use crate::structs::ExtraItem;
use crate::structs::Property;

impl<'a> ExtraItem<'a> {
    /// Key/value facts the app already has, labelled `label`.
    pub fn simple(label: &'a str, props: &'a [Property<'a>]) -> Self {
        Self {
            label: label.into(),
            props: props.into(),
        }
    }
}

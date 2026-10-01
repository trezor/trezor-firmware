//! A handle to a layout on the trusted side, so it survives being answered.
//!
//! Private. A block is one call to the app, but several screens to the person:
//! the block itself, the list of extras, one of the extras, then the block
//! again. Sending the block's request a second time used to build a second
//! layout on the trusted side, losing everything the first one held — scroll
//! position, page index, animation state — and paying a full construction to
//! show the person something they had already been looking at.
//!
//! A [`LayoutHandle`] is the app-side claim on such a layout: it picks a
//! handle number, the trusted side keeps the layout under it, and the layout
//! can be shown again instead of rebuilt. Dropping the handle closes it.
//!
//! Each request type maps to one [`UiV1`](crate::traits::ui::UiV1) method,
//! through [`Request`]; the op and the handle travel beside the request, so
//! the request itself describes only the content.

use crate::app_runtime2::get_ui_or_die;
use crate::traits::ui::{
    ConfirmAction, ConfirmProperties, ConfirmSummary, ConfirmValue, HANDLE_BITS, OP_ONCE, OP_OPEN,
    OP_REOPEN, SelectMenu, ShowNotice, ShowProperties, UiReply, UiV1Dyn as _,
};
use crate::{IntoAppResult, Result};

// ============================================================================
// Data types
// ============================================================================

/// A request the trusted side can draw: one `UiV1` method per type.
pub(super) trait Request {
    fn send(&self, op: u16, handle: u16) -> Result<UiReply>;
}

macro_rules! request {
    ($($ty:ident => $method:ident),* $(,)?) => {$(
        impl Request for $ty<'_> {
            fn send(&self, op: u16, handle: u16) -> Result<UiReply> {
                get_ui_or_die().$method(op, handle, self.clone()).into_app_result()
            }
        }
    )*};
}

request! {
    ConfirmAction => confirm_action,
    ConfirmValue => confirm_value,
    ConfirmSummary => confirm_summary,
    ConfirmProperties => confirm_properties,
    ShowProperties => show_properties,
    ShowNotice => show_notice,
    SelectMenu => select_menu,
}

/// A layout on the trusted side that survives being answered.
///
/// Dropping it closes the layout. Every screen a block shows more than once
/// should go through one of these, so nothing is left behind when the block
/// returns — including when it returns by `?` — and so re-showing restores
/// what the person was looking at rather than rebuilding it.
pub(super) struct LayoutHandle {
    handle: u16,
}

impl LayoutHandle {
    /// Claims a handle. Nothing is built on the trusted side until the first
    /// [`LayoutHandle::show`].
    pub fn new() -> Self {
        Self {
            handle: next_handle(),
        }
    }

    /// Builds the layout from `request` and blocks until the person acts on
    /// it.
    ///
    /// Use this for content the person has not seen, including the next
    /// chunk of something they have: the trusted side builds a new layout, so
    /// whatever the previous request said is gone.
    pub fn show(&self, request: &impl Request) -> Result<UiReply> {
        request.send(OP_OPEN, self.handle)
    }

    /// Shows the layout again, as the person left it.
    ///
    /// Only correct when `request` is the same one [`LayoutHandle::show`] was
    /// given: the trusted side reuses the layout it already has and ignores
    /// the payload. The payload is sent anyway so that a trusted side which no
    /// longer holds the layout can rebuild it rather than fail.
    pub fn reshow(&self, request: &impl Request) -> Result<UiReply> {
        request.send(OP_REOPEN, self.handle)
    }
}

impl Drop for LayoutHandle {
    fn drop(&mut self) {
        // Nothing useful can be done if this fails, and a panic here would
        // replace whatever error is already unwinding out of the block.
        let _ = get_ui_or_die().close(self.handle);
    }
}

// ============================================================================
// Entry point
// ============================================================================

/// Shows one screen that is never shown again, and blocks until the person
/// acts on it.
///
/// For content with no follow-up, where keeping a layout alive would only
/// leave something to clean up. No handle is involved.
pub(super) fn call_once(request: &impl Request) -> Result<UiReply> {
    request.send(OP_ONCE, 0)
}

// ============================================================================
// Internals
// ============================================================================

/// Hands out the next handle.
///
/// Handles are never reused while a [`LayoutHandle`] holds one: a block
/// nests only a few screens deep, and the counter covers every value the
/// handle bits allow before it comes round again.
///
/// A `static mut` rather than an atomic because an app is a single task,
/// which is the same assumption the rest of this crate makes.
fn next_handle() -> u16 {
    const MAX: u16 = (1 << HANDLE_BITS) - 1;
    static mut NEXT: u16 = 1;

    unsafe {
        let handle = NEXT;
        NEXT = if handle >= MAX { 1 } else { handle + 1 };
        handle
    }
}

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
//! The handle and the operation ride in the IPC message id rather than in the
//! payload, so the request itself describes only the content.

use rkyv::api::low::deserialize;
use rkyv::rancor::Failure;
use rkyv::{Archived, to_bytes};

use crate::core_services::services_or_die;
use crate::ipc::IpcMessage;
use crate::service::CoreIpcService;
use crate::structs::{TrezorUiEnum, UiReply};
use crate::util::Timeout;
use crate::{Error, Result};

// ============================================================================
// Constants
// ============================================================================

/// Build the layout, show it, and forget it.
const OP_ONCE: u16 = 0;
/// Build the layout and keep it alive under the handle.
const OP_OPEN: u16 = 1;
/// Show the layout already held under the handle, without rebuilding it.
const OP_REOPEN: u16 = 2;
/// Drop the layout held under the handle. Shows nothing.
const OP_CLOSE: u16 = 3;

/// Bits of the message id that carry the handle; the rest carry the op.
const HANDLE_BITS: u16 = 12;
const HANDLE_MASK: u16 = (1 << HANDLE_BITS) - 1;

// ============================================================================
// Data types
// ============================================================================

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
    pub fn show(&self, request: &TrezorUiEnum) -> Result<UiReply> {
        self.send(OP_OPEN, request)
    }

    /// Shows the layout again, as the person left it.
    ///
    /// Only correct when `request` is the same one [`LayoutHandle::show`] was
    /// given: the trusted side reuses the layout it already has and ignores
    /// the payload. The payload is sent anyway so that a trusted side which no
    /// longer holds the layout can rebuild it rather than fail.
    pub fn reshow(&self, request: &TrezorUiEnum) -> Result<UiReply> {
        self.send(OP_REOPEN, request)
    }

    /// Sends one message for this handle and decodes the reply.
    fn send(&self, op: u16, request: &TrezorUiEnum) -> Result<UiReply> {
        let bytes = to_bytes::<Failure>(request).map_err(|_| Error::ServiceError)?;
        raw_call(message_id(op, self.handle), bytes.as_ref())
    }
}

impl Drop for LayoutHandle {
    fn drop(&mut self) {
        // Nothing useful can be done if this fails, and a panic here would
        // replace whatever error is already unwinding out of the block.
        let _ = raw_call(message_id(OP_CLOSE, self.handle), &[]);
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
pub(super) fn call_once(request: &TrezorUiEnum) -> Result<UiReply> {
    let bytes = to_bytes::<Failure>(request).map_err(|_| Error::ServiceError)?;
    raw_call(message_id(OP_ONCE, 0), bytes.as_ref())
}

// ============================================================================
// Internals
// ============================================================================

/// Packs an operation and a handle into the 16-bit IPC message id.
fn message_id(op: u16, handle: u16) -> u16 {
    (op << HANDLE_BITS) | (handle & HANDLE_MASK)
}

/// Hands out the next handle.
///
/// Handles are never reused while a [`LayoutHandle`] holds one: a block
/// nests only a few screens deep, and the counter covers every value the
/// handle bits allow before it comes round again.
///
/// A `static mut` rather than an atomic because an app is a single task,
/// which is the same assumption the rest of this crate makes.
fn next_handle() -> u16 {
    static mut NEXT: u16 = 1;

    unsafe {
        let handle = NEXT;
        NEXT = if handle >= HANDLE_MASK { 1 } else { handle + 1 };
        handle
    }
}

/// Sends one UI message and blocks until the trusted side answers.
fn raw_call(id: u16, payload: &[u8]) -> Result<UiReply> {
    let message = IpcMessage::new(id, payload);
    let reply = services_or_die().call(CoreIpcService::Ui, &message, Timeout::max())?;

    let archived = rkyv::access::<Archived<UiReply>, Failure>(reply.data())
        .map_err(|_| Error::InvalidMessage)?;
    deserialize::<UiReply, Failure>(archived).map_err(|_| Error::InvalidMessage)
}

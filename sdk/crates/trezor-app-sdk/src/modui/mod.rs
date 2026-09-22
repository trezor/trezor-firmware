//! Building-block UI library: one typed function per UI block.
//!
//! The app decides which blocks to call and in what order. It picks which trust
//! signal a block carries (for example a notice's severity), but not what that
//! signal looks like or how it behaves: the confirm gesture, the styling and the
//! ButtonRequest identity are derived from the block rather than passed in.
//!
//! Every block takes a params struct — one constructor carrying every
//! parameter, optionals as `Option` — and returns one [`UiOutcome`]: **one
//! blocking call,
//! one value**. That is a property of this API, not of the transport underneath:
//! a block is free to make several IPC round trips internally, which is how
//! paging over long data will work. Cancellation is an outcome, not an error;
//! `Err` is reserved for transport, protocol and decode failures.
//!
//! This module **replaces** [`crate::ui`]; it is not a facade over it and not a
//! second option beside it. Once the apps are ported, `ui.rs` is deleted and
//! this module takes the `ui` name. The two coexisting is a migration window,
//! not the destination.
//!
//! The public surface above is the design; what carries it is scaffolding.
//! Today that means serializing onto the existing `TrezorUiEnum` wire and
//! borrowing [`crate::Error`] for failures, so blocks run against current
//! firmware with no core changes. Both get rewritten as the core side is built
//! out, and neither should force a change to a `ui::` signature when they do.
//!
//! # File layout
//!
//! Every file in this module is laid out the same way, with these sections in
//! this order, each skipped when it would be empty:
//!
//! 1. `Constants` — what the block fixes and the app therefore cannot choose.
//! 2. `Data types` — the params struct and anything that describes it.
//! 3. `Entry point` — the one public function.
//! 4. `Internals` — private helpers.
//!
//! **ButtonRequests are not this library's concern.** They tell the host a
//! screen is up, and they are emitted on the trusted side, which already knows
//! which block it is decoding — the block *is* the wire variant. So nothing
//! here supplies one, and the wire's `br_name`/`br_code` fields go out empty.
//! Until the dispatcher derives them, that means no ButtonRequest is sent for
//! a block at all; see the design notes.
//!
//! A block file is otherwise dull on purpose: params in, one `UiOutcome` out,
//! and the wire call in between. Anything cleverer than that belongs in a
//! shared helper (`paged`, `details`) so that no single block owns behaviour
//! the others should have too.
//!
//! Each file opens with its own `# Example`; the ones below show the shape all
//! of them share.
//!
//! # Example
//!
//! ```no_run
//! use trezor_app_sdk::modui::{self as ui, ConfirmAction, ConfirmValue, ValueKind};
//!
//! // A sequence of blocks is just a sequence of calls. Cancelling any one of
//! // them stops the flow, because `confirmed()` turns it into an error.
//! fn confirm_send(address: &str) -> trezor_app_sdk::Result<()> {
//!     ui::confirm_value(ConfirmValue::new(
//!         "Send",
//!         address,
//!         ValueKind::Address,
//!         Some("Recipient"),
//!         None,
//!         None,
//!         None,
//!     ))?
//!     .confirmed()?;
//!
//!     ui::confirm_action(ConfirmAction::new(
//!         "Send",
//!         "Sign the transaction?",
//!         None,
//!         None,
//!         None,
//!     ))?
//!     .confirmed()
//! }
//!
//! // Or handle the cancel yourself, when leaving is not an error.
//! fn offer_details(address: &str) -> trezor_app_sdk::Result<bool> {
//!     let params = ConfirmValue::new("Send", address, ValueKind::Address, None, None, None, None);
//!     Ok(ui::confirm_value(params)?.is_confirmed())
//! }
//! ```

// One file per block, plus the helpers they share. This list is the inventory;
// the re-exports below are grouped by rustfmt (`group_imports`), so do not try
// to arrange them by hand.
mod confirm_action;
mod confirm_data;
mod confirm_properties;
mod confirm_summary;
mod confirm_value;
mod details;
mod paged;
mod show_address;
mod show_notice;
mod show_success;

pub use confirm_action::{ConfirmAction, confirm_action};
pub use confirm_data::{ConfirmData, confirm_data};
pub use confirm_properties::{ConfirmProperties, confirm_properties};
pub use confirm_summary::{ConfirmSummary, confirm_summary};
pub use confirm_value::{ConfirmValue, Footer, ValueKind, confirm_value};
use rkyv::api::low::deserialize;
use rkyv::rancor::Failure;
use rkyv::{Archived, to_bytes};
pub use show_address::{ShowAddress, show_address};
pub use show_notice::{Severity, ShowNotice, show_notice};
pub use show_success::{ShowSuccess, show_success};
use ufmt::derive::uDebug;

use crate::core_services::services_or_die;
use crate::ipc::IpcMessage;
use crate::service::CoreIpcService;
/// A key/value fact, as shown in a list or on a details page.
pub use crate::structs::Property;
use crate::structs::{TrezorUiEnum, TrezorUiResult};
use crate::util::Timeout;
use crate::{Error, Result};

// ============================================================================
// Data types
// ============================================================================

/// What the user did with a block.
///
/// One shape for every block. `Cancelled` is an ordinary value, so it is easy
/// to ignore by accident — hence `#[must_use]` and [`UiOutcome::confirmed`],
/// which is the idiomatic way to require confirmation.
#[must_use]
#[derive(uDebug, Copy, Clone, PartialEq, Eq)]
pub enum UiOutcome {
    /// The user confirmed.
    Confirmed,
    /// The user left the block without confirming.
    Cancelled,
}

impl UiOutcome {
    /// Discharges the outcome, turning `Cancelled` into [`Error::Cancelled`].
    ///
    /// Use this when the caller cannot proceed without confirmation:
    /// `ui::confirm_action(params)?.confirmed()?`.
    pub fn confirmed(self) -> Result<()> {
        match self {
            Self::Confirmed => Ok(()),
            Self::Cancelled => Err(Error::Cancelled),
        }
    }

    /// Returns `true` if the user confirmed.
    pub fn is_confirmed(self) -> bool {
        matches!(self, Self::Confirmed)
    }
}

// ============================================================================
// Internals
// ============================================================================

/// Sends one screen over IPC and blocks until the user acts on it.
///
/// Returns the reply as-is. Most blocks want [`call`]; a block that drives
/// several screens of its own — see `confirm_data` — needs outcomes that the
/// public [`UiOutcome`] deliberately does not carry.
fn call_raw(request: &TrezorUiEnum) -> Result<TrezorUiResult> {
    let bytes = to_bytes::<Failure>(request).map_err(|_| Error::ServiceError)?;

    let message = IpcMessage::new(0, bytes.as_ref());
    let reply = services_or_die().call(CoreIpcService::Ui, &message, Timeout::max())?;

    let archived = rkyv::access::<Archived<TrezorUiResult>, Failure>(reply.data())
        .map_err(|_| Error::InvalidMessage)?;
    deserialize::<TrezorUiResult, Failure>(archived).map_err(|_| Error::InvalidMessage)
}

/// Sends a single-screen block and maps the reply to an outcome.
fn call(request: &TrezorUiEnum) -> Result<UiOutcome> {
    match call_raw(request)? {
        TrezorUiResult::Confirmed => Ok(UiOutcome::Confirmed),
        TrezorUiResult::Cancelled => Ok(UiOutcome::Cancelled),
        // A single-screen block never asks for navigation and never returns a
        // number, so core producing one is a protocol violation, not a gesture.
        TrezorUiResult::Back | TrezorUiResult::Info | TrezorUiResult::Integer(_) => {
            Err(Error::InvalidMessage)
        }
    }
}

//! Building-block UI library: one typed function per screen an app can show.
//!
//! An app decides which blocks to call and in what order, and what each one
//! says. It does not decide how anything looks or behaves: the confirm
//! gesture, the button words, the styling and the paging all follow from the
//! block, and are the same whichever app calls it.
//!
//! This module replaces [`crate::ui`]. The two exist side by side only while
//! apps are being ported; new code should use this one.
//!
//! # Blocks
//!
//! | Block | Shows | Extras |
//! |---|---|---|
//! | [`confirm_action`] | a question about an action | yes |
//! | [`confirm_value`] | one value, such as an address or an amount | yes |
//! | [`confirm_properties`] | a list of key/value facts | not yet |
//! | [`confirm_data`] | raw bytes, as hex, over as many pages as needed | yes |
//! | [`confirm_summary`] | the closing amount and fee of a transaction | yes |
//! | [`show_address`] | an address and its QR code, to check | not yet |
//! | [`show_notice`] | a notice of some [`Severity`] | depends on the severity |
//!
//! Every block takes a params struct built by one constructor carrying every
//! parameter, and blocks until the person answers.
//!
//! # Outcomes
//!
//! Every block returns [`UiOutcome`]: the person either confirmed or did not.
//! Cancelling is an answer, not a failure, so it arrives as `Ok`:
//!
//! - call [`UiOutcome::confirmed`] when the flow cannot go on without a yes —
//!   it turns [`UiOutcome::Cancelled`] into [`crate::Error::Cancelled`], which
//!   `?` then carries out of the handler;
//! - call [`UiOutcome::is_confirmed`] when leaving is a normal choice.
//!
//! How the person got there — which page they were on, whether they opened
//! the extras, which button they pressed — is never reported.
//!
//! # Step names
//!
//! Every block takes a *step name*, the `br` parameter: the name
//! the host sees for this screen, such as `"tron/send"` or
//! `"tron/approve/amount"`. Only the app knows its flow, so only the app can
//! name its steps. Use `"<app>/<step>"`, keep it stable across releases, and
//! give each distinct screen its own name — hosts and tests match on it.
//!
//! The library adds to it, and the app should not: screens that exist only
//! because a block offered extras are named after the block, with `/menu` and
//! `/details` appended. An empty name is refused.
//!
//! # Extras and the way out
//!
//! Most blocks take `extras`, a list of labelled [`ExtraItem`]s: more that the
//! person may want to see, such as the account a payment comes from. They are
//! reached from the block's screen, and looking at one comes back to the block
//! as the person left it. How they are presented is the library's choice and
//! may change without any signature changing.
//!
//! `cancel` offers a way to abandon the block, alongside the extras. Some
//! screens have a way out of their own as well, and each block says so where
//! it does. Where it does not, `cancel: false` with no extras leaves the
//! person able only to confirm — so pass `false` only for a step that has
//! nothing to refuse.
//!
//! A block that cannot show extras yet refuses a non-empty list rather than
//! draw a screen whose extras nobody can open; see the table above.
//!
//! # Errors
//!
//! A block returns `Err` only when it could not ask the question at all:
//!
//! - [`crate::Error::ValueError`] — the parameters cannot be shown: an empty
//!   step name, more extras than one screen can offer, extras on a block that
//!   cannot show them yet, or an extra of a kind not implemented yet.
//! - [`crate::Error::InvalidMessage`] — the device answered with something
//!   that makes no sense for this screen.
//! - Any other error — the request could not reach the device.
//!
//! Core also checks what it is asked to draw, and ends the app's session
//! instead of answering if it cannot draw it — for example a notice with
//! extras on a model whose notice screens have no menu.
//!
//! # Who is who
//!
//! Throughout these docs:
//!
//! - **the person** — the human holding the device, and the only one who
//!   confirms anything. Never "the user", which could equally mean the
//!   developer reading this.
//! - **the app** — the modular app calling these functions.
//! - **this library** — `modui`, which turns those calls into screens. It runs
//!   inside the app, on the untrusted side.
//! - **core** — the firmware past the IPC boundary, which draws the screens.
//!   Trusted.
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
//!         "app/send/recipient",
//!         &[],
//!     ))?
//!     .confirmed()?;
//!
//!     ui::confirm_action(ConfirmAction::new(
//!         "Send",
//!         "Sign the transaction?",
//!         None,
//!         None,
//!         "app/send/confirm",
//!         &[],
//!         true,
//!     ))?
//!     .confirmed()
//! }
//!
//! // Or handle the cancel yourself, when leaving is not an error.
//! fn offer_details(address: &str) -> trezor_app_sdk::Result<bool> {
//!     let params = ConfirmValue::new("Send", address, ValueKind::Address, None, None, None, "app/send", &[]);
//!     Ok(ui::confirm_value(params)?.is_confirmed())
//! }
//! ```

// For maintainers of this module; none of this is the app's concern.
//
// The public surface above is the design; what carries it is scaffolding.
// Today that means serializing onto the existing `TrezorUiEnum` wire and
// borrowing `crate::Error` for failures. Both get rewritten as core is built
// out, and neither should force a change to a block's signature when they do.
//
// When the wire is replaced, this is where it starts. Every block builds a
// `TrezorUiEnum` and hands it to `screen`, the only file that touches IPC — so
// a new request type means changing each block's final expression and how
// `screen` serializes, and nothing else here. What the new wire has to carry is
// already decided by this module: the block and its facts, the extras as data,
// and the op plus screen handle that today ride in the IPC message id because
// the payload had nowhere to put them. An earlier attempt at that type
// (`ui_wire.rs`, since deleted; see the git history) is worth reading first,
// for its list of things the app is deliberately not allowed to say.
//
// ButtonRequests: the app names the step and nothing else. The suffixes are
// `menu`'s. `br_code` is the legacy identifier, always `BR_CODE_OTHER`. Page
// counts, and whether a repeat is a new step, are core's.
//
// Every file is laid out the same way, each section skipped when empty:
// `Constants` (what the block fixes and the app cannot choose), `Data types`
// (the params struct), `Entry point` (the one public function), `Internals`.
// A block file is dull on purpose: params in, one `UiOutcome` out, the wire
// call in between. Anything cleverer belongs in a shared helper (`paged`,
// `menu`) so that no single block owns behaviour the others should have too.
// Each block's own example lives on its entry point, where rustdoc shows it:
// the block modules are private, so their `//!` docs are for maintainers.

// One file per block, plus the helpers they share. This list is the inventory;
// the re-exports below are grouped by rustfmt (`group_imports`), so do not try
// to arrange them by hand.
mod confirm_action;
mod confirm_data;
mod confirm_properties;
mod confirm_summary;
mod confirm_value;
mod extra;
mod menu;
mod paged;
mod screen;
mod show_address;
mod show_notice;

pub use confirm_action::{ConfirmAction, confirm_action};
pub use confirm_data::{ConfirmData, confirm_data};
pub use confirm_properties::{ConfirmProperties, confirm_properties};
pub use confirm_summary::{ConfirmSummary, confirm_summary};
pub use confirm_value::{ConfirmValue, Footer, ValueKind, confirm_value};
pub use extra::{Extra, ExtraItem};
use screen::Screen;
pub use show_address::{ShowAddress, show_address};
pub use show_notice::{Severity, ShowNotice, show_notice};
use ufmt::derive::uDebug;

/// A key/value fact, as shown in a list or on a page of extras.
pub use crate::structs::Property;
use crate::structs::{TrezorUiEnum, UiReply};
use crate::{Error, Result};

// ============================================================================
// Constants
// ============================================================================

/// The `ButtonRequestType` every block sends: `Other`, and nothing else.
///
/// Named for its value rather than its role, so that a call site says what
/// goes on the wire instead of implying there is a choice to make.
///
/// Legacy field, kept because hosts written before `br_name` switch on it. It
/// does not classify an extapp's screens and is not meant to: the name carries
/// the meaning, and every extapp call is `Other` by decision.
///
/// Stated once here rather than per block so that the day the field leaves the
/// wire, this constant and its uses go with it and nothing has to be
/// re-derived. Do not grow it into a per-block table.
const BR_CODE_OTHER: i32 = 1;

// ============================================================================
// Data types
// ============================================================================

/// What the person did with a block.
///
/// # Who uses this
///
/// - **Written by every block**, as the last thing it does, from a
///   [`UiReply`] and whatever the block knows that the reply does not.
/// - **Read by the modular app** — the only result type an app ever sees,
///   and the only one that is public.
/// - **Never crosses IPC.** It is deliberately narrower than the wire: no
///   pages, no menu indices, no navigation. A block asked a question and this
///   is the answer.
///
/// One shape for every block. `Cancelled` is an ordinary value, so it is easy
/// to ignore by accident — hence `#[must_use]` and [`UiOutcome::confirmed`],
/// which is the idiomatic way to require confirmation.
#[must_use]
#[derive(uDebug, Copy, Clone, PartialEq, Eq)]
pub enum UiOutcome {
    /// The person confirmed.
    Confirmed,
    /// The person left the block without confirming.
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

    /// Returns `true` if the person confirmed.
    pub fn is_confirmed(self) -> bool {
        matches!(self, Self::Confirmed)
    }
}

// ============================================================================
// Internals
// ============================================================================

/// Sends a block and returns what the person did with it.
///
/// When a block offers extras, looking at them and coming back brings the same
/// screen up again. The screen is reopened rather than rebuilt, so it is
/// found as it was left; that is invisible to the caller either way,
/// because the block is still one call and one answer.
fn call(
    request: &TrezorUiEnum,
    extras: &[ExtraItem<'_>],
    cancel: bool,
    br: Option<&str>,
) -> Result<UiOutcome> {
    // `None` is a block that announces nothing, which is the block's own
    // nature. An empty name is neither that nor a name, so it is a mistake:
    // the host would see a step with no identity, which is worse than silence.
    if br == Some("") {
        return Err(Error::ValueError("a step name must not be empty"));
    }

    let screen = Screen::new();
    let mut first = true;

    loop {
        let reply = if first {
            first = false;
            screen.show(request)?
        } else {
            screen.reshow(request)?
        };

        match reply {
            UiReply::Confirmed => return Ok(UiOutcome::Confirmed),
            UiReply::Cancelled => return Ok(UiOutcome::Cancelled),
            // The person asked for the extras. A block that offered none cannot
            // produce this, so it is a protocol violation rather than a gesture.
            UiReply::WantsMore => {
                if let Some(outcome) = menu::open(extras, cancel, br)? {
                    return Ok(outcome);
                }
            }
            // A block is a question with two answers. Anything else answers a
            // screen this is not — including a variant added to the wire after
            // this was written.
            _ => return Err(Error::InvalidMessage),
        }
    }
}

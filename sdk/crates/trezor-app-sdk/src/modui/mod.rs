//! Building-block UI library: one typed function per screen an app can show.
//!
//! An app decides which blocks to call and in what order, and what each one
//! says. It does not decide how anything looks or behaves: that is an
//! implementation detail of this library and core, invisible to the app.
//!
//! # Who is who
//!
//! - **the person** — the human holding the device, and the only one who
//!   confirms anything. Never "the user", which could equally mean the
//!   developer reading this.
//! - **the host** — the wallet or other software on the other end of the
//!   cable. The app serves the host's requests; step names and errors are
//!   reported to it.
//! - **the device** — the Trezor. Core runs on it, every screen is drawn
//!   on it, and the app is loaded onto it as data.
//! - **the app** — the modular app (an *extapp*) calling these functions.
//!   Low-trust: signed and verified before loading, but nothing here
//!   assumes it behaves.
//! - **this library** — `modui`, which turns the app's calls into screens.
//!   It runs inside the app, on the low-trust side.
//! - **core** — the firmware past the IPC boundary, which draws the screens.
//!   Trusted.
//!
//! And the words for what moves between them:
//!
//! - **a block** — one typed function of this library: one call, one
//!   question, one [`UiOutcome`], and the call does not return until the
//!   person has answered. The app's only way to show anything.
//! - **a screen** — what the person sees at one moment. A block may show
//!   several — its own, the extras menu, pages of content; the app never
//!   counts them.
//! - **the flow** — the app's sequence of blocks, in the order it calls
//!   them. The app owns it; this library never sees past one block.
//! - **a step name** — the `br` string naming one step of the flow for the
//!   host; see [step names](#step-names).
//! - **extras** — labelled pieces of additional information reachable from
//!   a block's screen; see [extras](#extras-and-the-way-out).
//! - **a session** — one run of the app, from the host's request to its
//!   response. A refusal ends it.
//!
//! # Blocks
//!
//! | Block | Shows | Extras |
//! |---|---|---|
//! | [`confirm_action`] | a question about an action | yes |
//! | [`confirm_value`] | one value, e.g. an address or an amount | yes |
//! | [`confirm_properties`] | a list of key/value facts | not yet |
//! | [`confirm_data`] | raw bytes, as hex, of any length - supports chunking | yes |
//! | [`confirm_summary`] | the closing amount and fee of a transaction - special commonly used case | yes |
//! | [`show_notice`] | a notice of some [`Severity`] | depends on the severity |
//!
//! Every block takes a params struct built by one constructor carrying every
//! parameter, and blocks until the person answers.
//!
//! WIP: possible additional blocks, none decided:
//!
//! ```text
//! show_qr          — a value as a QR code, to scan (needs a wire extension)
//! request_number   — the person enters a number (RequestNumber exists on the wire)
//! choose           — the person picks one of a list; a decisive screen, not
//!                    the navigational extras menu, and collides with the
//!                    no-app-menus rule — decide that boundary explicitly
//! ```
//!
//! Each returns its own outcome type with the same semantics; see the WIP
//! note under [outcomes](#outcomes).
//!
//! # Showing an address
//!
//! There is no `show_address` block: an app shows an address as
//! [`confirm_value`] with [`ValueKind::Address`], passing the account and
//! derivation path in `extras`.
//!
//! WIP: deliberate, and open to discussion. An address is a special case:
//! core's own receive screen is a multi-screen flow — chunked address, QR,
//! account info — whose refusal means a suspected mismatch, not a change of
//! mind. This library cannot express that flow, and refuses to imply it. The
//! QR view is therefore unsupported for now; it returns when the wire can
//! carry a QR view of its own.
//!
//! # Long content
//!
//! Content can be longer than one screen, and two different things split it,
//! each for its own reason:
//!
//! - **Chunking** is this library's, and exists because memory is limited. A
//!   request to core has to fit in one IPC message, on the order of a
//!   kilobyte, so data longer than that — the bytes given to [`confirm_data`],
//!   an [`Extra::Chunked`] extra — is cut into chunks, and each chunk is sent
//!   to core as a request of its own.
//! - **Pagination** is core's, and exists because the screen is small. Core
//!   splits whatever one request carries across as many screens as it takes
//!   — a screen holds a few hundred bytes at most, on the largest model — as
//!   the person scrolls. This library never sees it and never asks for it.
//!
//! Neither is the app's: an app hands over the whole value and gets one
//! outcome, and never learns how many chunks or pages it took.
//!
//! WIP: today the two meet only at a chunk's edge — each chunk is shown on
//! its own, core pages within it, and the person's yes on its last page
//! moves to the next chunk. The direction is one continuous read: the screen
//! says when it is paging towards the edge of the chunk it holds, and this
//! library fetches the next chunk before the person gets there — from the
//! app, or through the app from the host — so content of any length reads
//! as one document. That needs the total length known upfront, so core can
//! count pages across chunks, and a way for the screen to ask for more;
//! neither exists yet. The `chunked` module holds the details.
//!
//! # Outcomes
//!
//! Every block returns [`UiOutcome`]: the person either confirmed or did not.
//! Cancelling is an answer, not a failure, so it arrives as `Ok`:
//!
//! - call [`UiOutcome::confirmed`] when the flow cannot go on without a yes;
//! - call [`UiOutcome::is_confirmed`] when leaving is a normal choice.
//!
//! How the person got there — which page they were on, whether they opened
//! the extras, which button they pressed — is never reported.
//!
//! WIP: outcome types are a family, not a hierarchy. A block that asks for
//! something other than a yes — a value, a pick from a list — gets its own
//! type with the same semantics, written when the first one exists rather
//! than generalizing `UiOutcome` upfront:
//!
//! ```text
//! enum UiInput<u32> { Value(u32), Cancelled }   // .value()?  -> Ok(u32)    | Err(Cancelled)
//! enum UiChoice     { Picked(usize), Cancelled } // .picked()? -> Ok(usize) | Err(Cancelled)
//! ```
//!
//! ## The `confirmed()?` idiom
//!
//! Most screens must be a yes:
//!
//! ```text
//! ui::confirm_action(params)?.confirmed()?;
//! ```
//!
//! The first `?` unwraps the block's result; `.confirmed()` turns
//! `Cancelled` into [`crate::Error::Cancelled`], which the trailing `?`
//! returns from the function at once — nothing after it runs, and the host
//! sees the session ending with the person's refusal. Do not drop the
//! trailing `?` on a screen that must be a yes: a refusal would be ignored,
//! with the flow carrying on as if the person had confirmed. Omit it only
//! when the `Result` itself is the function's return value.
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
//! Every confirmation can be refused from its own screen, and that is never the
//! app's to switch off. A block whose screen always has a way out takes no
//! `cancel`. Where a block does take one, `cancel: true` adds a Cancel entry to
//! its extras that abandons the whole block.
//!
//! A block that cannot show extras yet refuses a non-empty list rather than
//! draw a screen whose extras nobody can open; see the table above.
//!
//! # Errors
//!
//! A block returns `Err` only when it could not ask the question at all. The
//! parameters are checked as the block is called, before anything is shown,
//! so a bad list of extras never fails halfway through a flow:
//!
//! - [`crate::Error::ValueError`] — the parameters cannot be shown: an empty
//!   step name, more extras than one screen can offer, extras on a block that
//!   cannot show them yet, or an extra of a kind not implemented yet.
//! - [`crate::Error::InvalidMessage`] — the device answered with something
//!   that makes no sense for this screen.
//! - Any other error — the request could not reach the device.
//!
//! Core also checks what it is asked to draw, per model, and the same call
//! may fare differently on each. What a model cannot draw at all — a screen
//! it has no implementation of — ends the session. What it can draw only
//! partially — a menu button it has no place for — it draws without, with a
//! warning, and the flow continues: on such a model the extras are
//! unreachable, but the app is not told.
//!
//! WIP: both of those outcomes are under discussion. A screen core cannot
//! draw kills the app's task outright — the blocking call never returns,
//! not even with an `Err`. Bluntly: there is no proper error path from core
//! to the app. The app can receive a service reply or nothing, and core's
//! only failure mode toward the app is stopping its task; errors flow to
//! the host, never to the app. The cheap fix is a `UiReply` failure variant
//! mapped to `Err` in `screen`; a fuller one is an error-report service
//! covering crypto and progress too. Likewise, a silently dropped menu
//! leaves the app believing its extras exist on every model; whether to
//! tell it is open.
//!
//! # Example
//!
//! ```no_run
//! use trezor_app_sdk::modui::{self as ui, Commitment, ConfirmAction, ConfirmValue, ValueKind};
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
//!         Commitment::Step,
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
//!         Commitment::Step,
//!         "app/send/confirm",
//!         &[],
//!     ))?
//!     .confirmed()
//! }
//!
//! // Or handle the cancel yourself, when leaving is not an error.
//! fn offer_details(address: &str) -> trezor_app_sdk::Result<bool> {
//!     let params = ConfirmValue::new("Send", address, ValueKind::Address, None, None, None, Commitment::Step, "app/send", &[]);
//!     Ok(ui::confirm_value(params)?.is_confirmed())
//! }
//! ```

// For maintainers of this module; none of this is the app's concern.
//
// `WIP:` paragraphs in the docs above mark open thoughts and discussion
// points, and are removed before merge.
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
// call in between. Anything cleverer belongs in a shared helper (`chunked`,
// `menu`) so that no single block owns behaviour the others should have too.
// Each block's own example lives on its entry point, where rustdoc shows it:
// the block modules are private, so their `//!` docs are for maintainers.

// One file per block, plus the helpers they share. This list is the inventory;
// the re-exports below are grouped by rustfmt (`group_imports`), so do not try
// to arrange them by hand.
mod chunked;
mod confirm_action;
mod confirm_data;
mod confirm_properties;
mod confirm_summary;
mod confirm_value;
mod extra;
mod menu;
mod screen;
mod show_notice;

pub use confirm_action::{ConfirmAction, confirm_action};
pub use confirm_data::{ConfirmData, confirm_data};
pub use confirm_properties::{ConfirmProperties, confirm_properties};
pub use confirm_summary::{ConfirmSummary, confirm_summary};
pub use confirm_value::{ConfirmValue, Footer, ValueKind, confirm_value};
pub use extra::{Extra, ExtraItem};
use screen::Screen;
pub use show_notice::{Severity, ShowNotice, show_notice};
use ufmt::derive::uDebug;

/// A key/value fact, as shown in a list or on an extra's screen.
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

/// What confirming a block commits the person to.
///
/// The app knows which of its screens is the one that signs; the library does
/// not. The app says so here, and the library turns it into the gesture —
/// today a hold rather than a tap — so the person's last yes is harder to give
/// by accident. The gesture itself is not the app's to name.
#[derive(uDebug, Copy, Clone, PartialEq, Eq)]
pub enum Commitment {
    /// One step of a longer flow. Confirming it only moves on.
    Step,
    /// The last confirmation before the app signs or otherwise acts.
    Final,
}

/// What the person did with a confirmation block.
///
/// # Who uses this
///
/// - **Written by every confirmation block**, as the last thing it does, from
///   a [`UiReply`] and whatever the block knows that the reply does not.
/// - **Read by the modular app**, as the answer to a question that has only
///   yes and no.
/// - **Never crosses IPC.** It is deliberately narrower than the wire: no
///   chunks, no menu indices, no navigation. A block asked a question and this
///   is the answer.
///
/// A block that asks for something other than a yes — a value, a pick from
/// a list — returns a different type with the same semantics, when the first
/// one exists.
///
/// `Cancelled` is an ordinary value, so it is easy to ignore by accident —
/// hence `#[must_use]` and [`UiOutcome::confirmed`], which is the idiomatic
/// way to require confirmation.
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
    menu::check_extras(extras, cancel)?;

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

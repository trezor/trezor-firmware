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
//!   question, one [`UiReply`], and the call does not return until the
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
//! A block returns [`UiReply`]: the person's answer as it crossed the
//! wire, not a translation of it. Cancelling is an answer, not a failure,
//! so it arrives as `Ok`. How the person got there — which page they were
//! on, whether they opened the extras, which button they pressed — is
//! never reported.
//!
//! Which replies can arrive is fixed by the parameters, not by filtering
//! after the fact: a screen renders a back affordance only when its block
//! takes `back`, a Cancel entry only when it takes `cancel`, and a reply
//! the parameters could not produce — a `Backward` from a block that
//! shows no way back — is a protocol violation, answered with
//! [`crate::Error::InvalidMessage`]. What the library answers itself — a
//! `WantsMore` by opening the extras, page turns inside one chunk — never
//! reaches the caller; `ConfirmedAll` does, from chunked content the
//! person accepted without reading: a yes, with that fact attached.
//!
//! Reading the answer is a `match`; the caller decides what each answer
//! means. For the most common case — a screen that must be a yes —
//! `.confirmed()` and `.is_confirmed()` are sugar for that decision, so a
//! refusal needs no arm of its own.
//!
//! `Backward` is the one answer no block can give yet: the wire has no
//! `back` parameter, so no screen offers the gesture. It arrives with
//! [going back](#going-back).
//!
//! WIP: with the raw reply public, sibling outcome types are subsumed:
//! `Choice` already rides the wire for a pick from a list, and an input
//! block adds its variant there — carrying its value — rather than a
//! parallel enum family. Written when the first such block exists.
//!
//! ## The `confirmed()?` idiom
//!
//! Most screens must be a yes:
//!
//! ```text
//! ui::confirm_action(params)?.confirmed()?;
//! ```
//!
//! The first `?` unwraps the block's result; `.confirmed()` turns every
//! answer that is not a yes into [`crate::Error::Cancelled`], which the
//! trailing `?`
//! returns from the function at once — nothing after it runs, and the host
//! sees the session ending with the person's refusal. Do not drop the
//! trailing `?` on a screen that must be a yes: a refusal would be ignored,
//! with the flow carrying on as if the person had confirmed. Omit it only
//! when the `Result` itself is the function's return value.
//!
//! # Going back
//!
//! Back is a parameter, like the way out. A block that takes `back` — off
//! by default — renders a back affordance on its screen, and only such a
//! block answers `Backward`. A lone block has nothing to go back to; it
//! leaves `back` off, and the answer cannot even arrive.
//!
//! Sequences are where it matters. A sequence that wants earlier steps
//! revisitable sets `back` on every step after the first, and answers
//! `Backward` by showing the previous step again. `confirm_linear_flow`
//! is that, library-owned: the app hands over the steps, the flow sets
//! `back` itself — never on the first — and returns when the last step
//! is confirmed or any is refused. A sequence of another shape — a
//! review-and-edit loop, a branch — matches on `Backward` itself; the
//! raw replies are public for exactly that.
//!
//! WIP: half-built. [`confirm_linear_flow`] exists and owns the ordering,
//! but no block takes `back` yet, so no step's screen offers the gesture
//! and no `Backward` can arrive. The parameter lands with the ethereum
//! port; the flow is ready for it.
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
//! # Progress
//!
//! Not everything the app shows waits for the person. While the app works —
//! hashing, fetching, signing — it can hold up a progress, so the person
//! sees that the device has not stalled. A progress is not a block: it asks
//! nothing, answers nothing, and never blocks. It appears when the work
//! starts and disappears when it ends, including through `?`, because the
//! app never ends one by hand: the library owns the ending, the same way it
//! owns a block's screens.
//!
//! Two forms cover the usual cases, both closures: [`progress`] for work
//! that needs no step reporting, [`progress_with`] for work that does —
//! [`Progress::step`] along the way, in whatever unit the app counts. The
//! percent is never the app's arithmetic: the library computes it from the
//! [`Total`] given at the start, and a step past the total pins the bar
//! full rather than wrapping it. [`Total::Unknown`] shows motion without
//! a fill, and steps on it do nothing.
//!
//! A step is deliberately infallible. It is a status note, not a step of
//! the work: an update that cannot be delivered must not abort the work it
//! describes, so the person at worst sees a stale bar until the next one.
//!
//! [`Progress::start`] is the escape hatch for work that cannot be a
//! closure, and carries the one trap: the binding must hold the value,
//! because dropping it is what ends the progress. `let _ = ...` ends it
//! at once.
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
//!   that makes no sense for this screen, including a reply its parameters
//!   could not have produced.
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
// `TrezorUiEnum` and hands it to `layout`, the only file that touches IPC — so
// a new request type means changing each block's final expression and how
// `layout` serializes, and nothing else here. What the new wire has to carry is
// already decided by this module: the block and its facts, the extras as data,
// and the op plus layout handle that today ride in the IPC message id because
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
// A block file is dull on purpose: params in, one `UiReply` out, the wire
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
mod confirm_linear_flow;
mod confirm_properties;
mod confirm_summary;
mod confirm_value;
mod extra;
mod layout;
mod menu;
mod progress;
mod show_notice;

pub use confirm_action::{ConfirmAction, confirm_action};
pub use confirm_data::{ConfirmData, confirm_data};
pub use confirm_linear_flow::confirm_linear_flow;
pub use confirm_properties::{ConfirmProperties, confirm_properties};
pub use confirm_summary::{ConfirmSummary, confirm_summary};
pub use confirm_value::{ConfirmValue, Footer, ValueKind, confirm_value};
pub use extra::{Extra, ExtraItem};
use layout::LayoutHandle;
pub use progress::{Progress, Total, progress, progress_with};
pub use show_notice::{Severity, ShowNotice, show_notice};
use ufmt::derive::uDebug;

/// A key/value fact, as shown in a list or on an extra's screen.
pub use crate::structs::Property;
use crate::structs::TrezorUiEnum;
/// The person's answer to a block: the wire reply, as it came.
pub use crate::structs::UiReply;
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

/// The common readings of a block's answer.
///
/// The reply itself is the wire's — one variant per gesture, defined beside
/// the other wire types — and every variant an app can receive is one the
/// block's parameters asked for; see [outcomes](crate::modui#outcomes).
/// These methods are the readings most callers want, so a refusal needs no
/// arm of its own.
impl UiReply {
    /// Discharges the answer, turning every reply that is not a yes into
    /// [`Error::Cancelled`].
    ///
    /// Use this when the caller cannot proceed without confirmation:
    /// `ui::confirm_action(params)?.confirmed()?`.
    pub fn confirmed(self) -> Result<()> {
        match self {
            Self::Confirmed | Self::ConfirmedAll => Ok(()),
            _ => Err(Error::Cancelled),
        }
    }

    /// Returns `true` if the person confirmed.
    ///
    /// A `ConfirmedAll` counts: the person accepted the rest without reading
    /// it, which is still a yes.
    pub fn is_confirmed(self) -> bool {
        matches!(self, Self::Confirmed | Self::ConfirmedAll)
    }
}

// ============================================================================
// Internals
// ============================================================================

/// Sends a block and returns what the person did with it.
///
/// When a block offers extras, looking at them and coming back brings the same
/// screen up again. The layout is reopened rather than rebuilt, so it is
/// found as the person left it; that is invisible to the caller either way,
/// because the block is still one call and one answer.
fn call(
    request: &TrezorUiEnum,
    extras: &[ExtraItem<'_>],
    cancel: bool,
    br: Option<&str>,
) -> Result<UiReply> {
    // `None` is a block that announces nothing, which is the block's own
    // nature. An empty name is neither that nor a name, so it is a mistake:
    // the host would see a step with no identity, which is worse than silence.
    if br == Some("") {
        return Err(Error::ValueError("a step name must not be empty"));
    }
    menu::check_extras(extras, cancel)?;

    let layout = LayoutHandle::new();
    let mut first = true;

    loop {
        let reply = if first {
            first = false;
            layout.show(request)?
        } else {
            layout.reshow(request)?
        };

        match reply {
            // The answers, passed on as they came. `ConfirmedAll` is a yes
            // with the fact that the rest was skipped attached, for screens
            // that offer the skip.
            UiReply::Confirmed | UiReply::Cancelled | UiReply::ConfirmedAll => return Ok(reply),
            // The person asked for the extras. A block that offered none cannot
            // produce this, so it is a protocol violation rather than a gesture.
            UiReply::WantsMore => {
                if let Some(reply) = menu::open(extras, cancel, br)? {
                    return Ok(reply);
                }
            }
            // The rest answer a screen this is not — a page turn, a pick from
            // a list, a way back no block offers — including a variant added
            // to the wire after this was written.
            _ => return Err(Error::InvalidMessage),
        }
    }
}

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
//!   question, one answer (see [outcomes](#outcomes)), and the call does
//!   not return until the person has answered. The app's only way to show anything.
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
//! | [`confirm::action`] | a question about an action | yes |
//! | [`confirm::value`] | one value, e.g. an address or an amount | yes |
//! | [`confirm::properties`] | a list of key/value facts | yes |
//! | [`confirm::data`] | raw bytes, as hex, of any length | yes |
//! | [`confirm::summary`] | the closing amount and fee of a transaction | yes |
//! | [`notice::show`] | a notice of some [`notice::Severity`] | depends on the severity |
//!
//! Every block is one function taking every parameter, and blocks until the
//! person answers.
//!
//! WIP: possible additional blocks, none decided:
//!
//! ```text
//! show_qr          — a value as a QR code, to scan (needs a wire extension)
//! request_number   — the person enters a number (needs a wire extension)
//! choose           — the person picks one of a list; a decisive screen, not
//!                    the navigational extras menu, and collides with the
//!                    no-app-menus rule — decide that boundary explicitly
//! ```
//!
//!
//! # Showing an address
//!
//! There is no `show_address` block: an app shows an address as
//! [`confirm::value`] with [`confirm::ValueKind::Address`], passing the account and
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
//! - **Chunking** is the firmware's, and exists because core's memory is
//!   limited: long data — the bytes given to [`confirm::data`] — is cut into
//!   chunks so core never holds a whole blob at once, and each chunk is sent to
//!   core as a request of its own. It happens behind the block's one call,
//!   outside the app.
//! - **Pagination** is core's, and exists because the screen is small. Core
//!   splits whatever one request carries across as many screens as it takes
//!   — a screen holds a few hundred bytes at most, on the largest model — as
//!   the person scrolls.
//!
//! Neither is the app's: an app hands over the whole value and gets one
//! outcome, and never learns how many chunks or pages it took.
//!
//! WIP: today the two meet only at a chunk's edge — each chunk is shown on
//! its own, core pages within it, and the person's yes on its last page
//! moves to the next chunk. The direction is one continuous read: the screen
//! says when it is paging towards the edge of the chunk it holds, and the
//! next chunk is fetched before the person gets there — from the app, or
//! through the app from the host — so content of any length reads as one
//! document. That needs the total length known upfront, so core can count
//! pages across chunks, and a way for the screen to ask for more; neither
//! exists yet. The chunk loop in `core/embed/api` holds the details.
//!
//! # Outcomes
//!
//! What a block returns depends on what kind of block it is:
//!
//! - **A confirmation** ([`confirm`]) and **a notice** ([`notice::show`])
//!   return `Result<()>`: `Ok(())` when the person said yes or moved on,
//!   and `Err(`[`crate::Error::Cancelled`]`)` when they backed out, by
//!   whatever way out the model offers. A notice answers `Cancelled` only
//!   where it offers a way back out.
//! - **A progress** ([`progress`]) returns what the work returned.
//!
//! A cancel is an `Err` so that `?` stops the flow on it: nothing after the
//! refused screen runs, and the host sees the session end with the person's
//! refusal. Most screens must be a yes, so this is the case that should cost
//! nothing to write and nothing to forget:
//!
//! ```text
//! confirm::action(..)?;
//! ```
//!
//! Where backing out is not the end of the flow, match it:
//!
//! ```text
//! match confirm::action(..) {
//!     Ok(()) => { /* yes */ }
//!     Err(Error::Cancelled) => { /* no, carry on */ }
//!     Err(e) => return Err(e),
//! }
//! ```
//!
//! No other `Err` comes back: a failure ends the app (see [errors](#errors)).
//!
//! How the person got there — which page they were on, whether they opened
//! the extras, which button they pressed — is never reported: it happens in
//! core, and only the block's answer comes back.
//!
//! # Step names
//!
//! Every block takes a *step name*, the `br` parameter: the name
//! the host sees for this screen, such as `"tron/send"` or
//! `"tron/approve/amount"`. Only the app knows its flow, so only the app can
//! name its steps. Use `"<app>/<step>"`, keep it stable across releases, and
//! give each distinct screen its own name — hosts and tests match on it.
//!
//! Core adds to it, and the app should not: screens that exist only because a
//! block offered extras are named after the block, with `/menu` and
//! `/details` appended.
//!
//! # Extras and the way out
//!
//! Every block takes `extras`, a list of labelled [`ExtraItem`]s: more that
//! the person may want to see, such as the account a payment comes from. They
//! travel with the block's request, and core presents them from the block's
//! screen; looking at one comes back to the block as the person left it. How
//! they are presented is core's, per model, and may change without any
//! signature changing.
//!
//! WIP: where a screen has no menu, its extras cannot be reached: bolt has no
//! menus, delizia's summary draws without one, and notices have one only for
//! some severities (see [`notice`]).
//!
//! Every confirmation can be refused, and that is never the app's to switch
//! off: no confirmation takes `cancel`. Where the way out is drawn — on the
//! screen, or in the extras on a model whose menu button takes its place — is
//! the model's, and the app neither sees nor chooses it. A notice takes
//! `cancel`: whether the person may back out of it.
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
//! Two forms cover the usual cases, both closures: [`progress::run`] for work
//! that needs no step reporting, [`progress::run_with`] for work that does —
//! [`progress::Progress::step`] along the way, in whatever unit the app counts. The
//! percent is never the app's arithmetic: core computes it from the
//! [`progress::Total`] given at the start, and a step past the total pins the bar
//! full rather than wrapping it. [`progress::Total::Unknown`] shows motion without
//! a fill, and steps on it do nothing.
//!
//! A step is deliberately infallible. It is a status note, not a step of
//! the work: an update that cannot be delivered must not abort the work it
//! describes, so the person at worst sees a stale bar until the next one.
//!
//! [`progress::Progress::start`] is the escape hatch for work that cannot be a
//! closure, and carries the one trap: the binding must hold the value,
//! because dropping it is what ends the progress. `let _ = ...` ends it
//! at once.
//!
//! # Errors
//!
//! A block's only `Err` is [`crate::Error::Cancelled`] (see
//! [outcomes](#outcomes)), and a progress has none. A failure — the request
//! did not reach core, or the answer cannot be read — ends the app, and the
//! call never returns.
//!
//! The library checks nothing itself. A request core cannot take — more
//! extras than a model's menu holds, more than fits in one IPC message —
//! stops the app: that is a mistake in the app, not a state to handle.
//!
//! Core also checks what it is asked to draw, per model, and the same call
//! may fare differently on each. What a model cannot draw at all — a screen
//! it has no implementation of — ends the session. What it can draw only
//! partially — a menu button it has no place for — it draws without, with a
//! warning, and the flow continues: on such a model the extras are
//! unreachable, but the app is not told.
//!
//! WIP: both of those outcomes are under discussion. There is no error path
//! from core to the app: a screen core cannot draw stops the app's task, and
//! the blocking call never returns. The cheap fix is a `TrezorUiResult`
//! failure variant carrying the reason, on which the block ends the app with
//! it; a fuller one is an error-report service covering crypto and progress
//! too. Whether to tell the app about a dropped menu is open.
//!
//! WIP: contract breaks left: a `Done` notice waits for a tap on bolt and
//! caesar, and notices ignore `cancel`; see [`notice`].
//!
//! # Example
//!
//! ```no_run
//! use trezor_app_sdk::modui::{Commitment, confirm};
//!
//! // A sequence of blocks is just a sequence of calls. Cancelling any one of
//! // them stops the flow, because a cancel is an `Err`.
//! fn confirm_send(address: &str) -> trezor_app_sdk::Result<()> {
//!     confirm::value(
//!         "Send",
//!         address,
//!         confirm::ValueKind::Address,
//!         Some("Recipient"),
//!         None,
//!         None,
//!         Commitment::Step,
//!         "app/send/recipient",
//!         &[],
//!     )?;
//!
//!     confirm::action(
//!         "Send",
//!         "Sign the transaction?",
//!         None,
//!         None,
//!         Commitment::Step,
//!         "app/send/confirm",
//!         &[],
//!     )
//! }
//!
//! // Or handle the cancel yourself, when leaving is not the end of the flow.
//! fn offer_details(address: &str) -> trezor_app_sdk::Result<bool> {
//!     let kind = confirm::ValueKind::Address;
//!     match confirm::value("Send", address, kind, None, None, None, Commitment::Step, "app/send", &[]) {
//!         Ok(()) => Ok(true),
//!         Err(trezor_app_sdk::Error::Cancelled) => Ok(false),
//!         Err(e) => Err(e),
//!     }
//! }
//! ```

// For maintainers of this module; none of this is the app's concern.
//
// `WIP:` paragraphs in the docs above mark open thoughts and discussion
// points, and are removed before merge.
//
// This module is compiled into every app, so it holds as little code as it
// can: a block puts its arguments into the `crate::structs` request and makes
// one `UiV1` call. Anything with behaviour — chunking, the menu, the
// progress count, every default — is in the firmware: `core/embed/api` (which
// runs on the app's task) or core.
//
// One type per request, from the app to core. The request crosses the `UiV1`
// vtable as is, `core/embed/api` serializes that same value, and core reads
// it archived. Core runs the block's menu itself and replies once. There are
// no mirror types and no conversions in between.
//
// So a new block means a `structs` type and its `TrezorUiEnum` variant, an
// arm in core's dispatch, and the block's function here. Every block goes
// through `UiV1::ui_call`, except `confirm::data`: its own
// `UiV1::confirm_data` lets the firmware send the data in chunks.
//
// ButtonRequests: the app names the step and nothing else. The `/menu` and
// `/details` suffixes are core's, as are the `ButtonRequestType` (always
// `Other`), page counts, and whether a repeat is a new step.
//
// Layout: the public surface is this file plus one module per kind of block
// (`confirm`, `notice`, `progress`). A public file holds only what an app
// may use — the block's function and the types an app names — so that
// reading a public file is reading the API.
//
// A block file is dull on purpose: arguments in, one answer out, the wire
// call in between. Anything cleverer belongs in the firmware, not here.
// Each block's own example lives on its function, where rustdoc shows it;
// the files inside `confirm/` are private modules re-exported by
// `confirm/mod.rs`, so their `//!` docs are for maintainers. The re-exports
// below are grouped by rustfmt (`group_imports`), so do not try to arrange
// them by hand.
pub mod confirm;
mod extra;
pub mod notice;
pub mod progress;

// ============================================================================
// Data types
// ============================================================================
pub use extra::ExtraItem;

pub use crate::structs::Commitment;
/// A key/value fact, as shown in a list or on an extra's screen.
pub use crate::structs::Property;

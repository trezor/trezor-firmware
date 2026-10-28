//! Building-block UI library: one typed function per decision an app asks.
//!
//! An app decides which decisions to ask and in what order, and what each one
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
//! - **a layout** — one typed function of this library: one call, one
//!   question, one answer (see [outcomes](#outcomes)), and the call does
//!   not return until the person has answered. The app's only way to show
//!   anything.
//! - **a fact** — one thing the person reads, a [`Field`]. What it *is*
//!   decides how it looks; see [facts](#facts).
//! - **a screen** — what the person sees at one moment. A layout may show
//!   several — its own, the extras menu, pages of content; the app never
//!   counts them.
//! - **the flow** — the app's sequence of layouts, in the order it calls
//!   them. The app owns it; this library never sees past one layout.
//! - **a step name** — the name of one step of the flow for the host; see
//!   [step names](#step-names).
//! - **extras** — labelled pieces of additional information reachable from
//!   a review's screen; see [extras](#extras-and-the-way-out).
//! - **a session** — one run of the app, from the host's request to its
//!   response. A refusal ends it.
//!
//! # Layouts
//!
//! | Layout | Shows | Extras |
//! |---|---|---|
//! | [`review`] | facts to read before a yes | yes |
//! | [`danger`] | facts that make going on risky | — |
//! | [`details`] | facts the person may skip | — |
//! | [`verify_address`] | one of the person's own addresses | — |
//! | [`verify_pubkey`] | one of the person's own public keys | — |
//! | [`done`] | the end of the flow | — |
//!
//! Every layout is one function taking every parameter, and does not return
//! until the person answers — except [`done`], which returns at once.
//!
//! WIP: possible additional layouts, none decided:
//!
//! ```text
//! request_number   — the person enters a number (needs a wire extension)
//! choose           — the person picks one of a list; a decisive screen, not
//!                    the navigational extras menu, and collides with the
//!                    no-app-menus rule — decide that boundary explicitly
//! ```
//!
//! # Facts
//!
//! Every layout that asks takes its content as [`Field`]s. The constructor
//! names what the value *is* — words, a sum, something to compare character
//! by character, raw bytes, a note, a warning — and core decides how that kind
//! looks on every model: its styling, its grouping, its paging and its font.
//! The app never picks a style, and one list may mix all six kinds.
//!
//! # Outcomes
//!
//! What a layout returns depends on what kind of layout it is:
//!
//! - **[`review`], [`danger`], [`verify_address`] and [`verify_pubkey`]**
//!   return `Result<()>`: `Ok(())` when the person said yes, and
//!   `Err(`[`crate::Error::Cancelled`]`)` when they refused, by whatever
//!   way out the model offers.
//! - **[`details`]** returns `Result<`[`Details`]`>`: `Show` when the person
//!   asked for the details, `Skip` when they accepted without them, and
//!   `Err(Cancelled)` when they refused.
//! - **[`done`]** returns nothing: it is the last screen of the flow.
//! - **A progress** ([`progress`]) returns what the work returned.
//!
//! A cancel is an `Err` so that `?` stops the flow on it: nothing after the
//! refused screen runs, and the host sees the session end with the person's
//! refusal. Most screens must be a yes, so this is the case that should cost
//! nothing to write and nothing to forget:
//!
//! ```text
//! modui::review("send", "Send", &facts).confirm()?;
//! ```
//!
//! Where refusing is not the end of the flow, match it:
//!
//! ```text
//! match modui::details("message", "Confirm message", &facts) {
//!     Ok(Details::Show) => { /* the person wants the details */ }
//!     Ok(Details::Skip) => { /* they accepted without them */ }
//!     Err(_) => { /* no, carry on */ }
//! }
//! ```
//!
//! How the person got there — which page they were on, whether they opened
//! the extras, which button they pressed — is never reported: it happens in
//! core, and only the layout's answer comes back.
//!
//! # Step names
//!
//! Every layout takes a *step name*: the name the host sees for this screen,
//! relative to the app, such as `"send"` or `"approve/amount"`. Only the app
//! knows its flow, so only the app can name its steps. Keep it stable across
//! releases, and give each distinct screen its own name — hosts and tests match
//! on it.
//!
//! Core adds the app's identity in front, and the app should not: `"send"`
//! reaches the host as `"tron.trezor.com/send"`. Screens that exist only
//! because a review offered extras are named after the review, with `/menu` and
//! `/details` appended.
//!
//! # Extras and the way out
//!
//! A [`review`] can take extras, a list of labelled facts the person may want
//! to see, such as the account a payment comes from; see
//! [`Review::extra`]. They travel with the review's request, and core presents
//! them from the review's screen; looking at one comes back to the review as the
//! person left it. How they are presented is core's, per model, and may change
//! without any signature changing.
//!
//! Up to five extras per review: the menu holds six entries and one is the way
//! out. A sixth is an `Err`; see [errors](#errors).
//!
//! WIP: where a screen has no menu, its extras cannot be reached: bolt has no
//! menus.
//!
//! Every layout can be refused, and that is never the app's to switch off: no
//! layout takes `cancel`. Where the way out is drawn — on the screen, or in the
//! extras on a model whose menu button takes its place — is the model's, and the
//! app neither sees nor chooses it.
//!
//! # Long content
//!
//! Content can be longer than one screen, and two different things split it,
//! each for its own reason:
//!
//! - **Chunking** is the firmware's, and exists because core's memory is
//!   limited: long data — the bytes given to [`Field::data`] — is cut into
//!   chunks so core never holds a whole blob at once. The bytes stay in the
//!   app; core pulls each chunk while the person pages, and the call does not
//!   return until the last one is read.
//! - **Pagination** is core's, and exists because the screen is small. Core
//!   splits whatever one request carries across as many screens as it takes
//!   — a screen holds a few hundred bytes at most, on the largest model — as
//!   the person scrolls.
//!
//! Neither is the app's: an app hands over the whole value and gets one
//! outcome, and never learns how many chunks or pages it took.
//!
//! WIP: until core pulls the data itself (P10), a `data` field travels inline
//! and is capped at 1024 bytes; a longer one is
//! [`crate::Error::ValueError`].
//!
//! # Progress
//!
//! Not everything the app shows waits for the person. While the app works —
//! hashing, fetching, signing — it can hold up a progress, so the person sees
//! that the device has not stalled. A progress is not a layout: it asks nothing,
//! answers nothing, and never layouts. It appears when the work starts and
//! disappears when it ends, including through `?`, because the app never ends one
//! by hand: the library owns the ending, the same way it owns a layout's screens.
//!
//! [`progress`] runs the work as one closure and hands it a [`Progress`] to
//! report steps with, in whatever unit the app counts. The percent is never the
//! app's arithmetic: core computes it from the total given at the start, and a
//! step past the total pins the bar full rather than wrapping it. No total shows
//! motion without a fill, and steps on it do nothing.
//!
//! A step is deliberately infallible. It is a status note, not a step of the
//! work: an update that cannot be delivered must not abort the work it
//! describes, so the person at worst sees a stale bar until the next one.
//!
//! # Errors
//!
//! A layout's `Err` is [`crate::Error::Cancelled`] when the person refuses
//! (see [outcomes](#outcomes)). What the library can tell before it asks —
//! more than five extras, more than one `data` field, a `data` field too long
//! to travel inline — is also an `Err`, and `?` ends the flow on it, the same
//! way: that is a mistake in the app, not a state to handle.
//!
//! A failure — the request did not reach core, or the answer cannot be read —
//! ends the app, and the call never returns. So does a request core cannot
//! draw: that is a mistake in the app too, but only core can see it.
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
//! failure variant carrying the reason, on which the layout ends the app with
//! it; a fuller one is an error-report service covering crypto and progress
//! too. Whether to tell the app about a dropped menu is open.
//!
//! # Example
//!
//! ```no_run
//! use trezor_app_sdk::modui::{self, Details, Field};
//!
//! // A sequence of layouts is just a sequence of calls. Cancelling any one of
//! // them stops the flow, because a cancel is an `Err`.
//! fn confirm_send(address: &str, amount: &str) -> trezor_app_sdk::Result<()> {
//!     modui::review("send", "Send", &[Field::address("Recipient", address)]).confirm()?;
//!
//!     modui::review("summary", "Send", &[Field::amount("Amount", amount)]).confirm_final()
//! }
//!
//! // Or handle the cancel yourself, when leaving is not the end of the flow.
//! fn offer_details(address: &str) -> bool {
//!     match modui::details("send", "Send", &[Field::address("Recipient", address)]) {
//!         Ok(Details::Show) => true,
//!         Ok(Details::Skip) => false,
//!         Err(_) => false,
//!     }
//! }
//! ```

// For maintainers of this module; none of this is the app's concern.
//
// `WIP:` paragraphs in the docs above mark open thoughts and discussion
// points, and are removed before merge.
//
// This module is compiled into every app, so it holds as little code as it
// can: a layout puts its arguments into the `crate::structs` request and makes
// one `UiV1` call. Anything with behaviour — chunking, the menu, the
// progress count, every default — is in the firmware: `core/embed/api` (which
// runs on the app's task) or core.
//
// One type per request, from the app to core. The request crosses the `UiV1`
// vtable as is, `core/embed/api` serializes that same value, and core reads
// it archived. Core runs the layout's menu itself and replies once. There are
// no mirror types and no conversions in between.
//
// So a new layout means a `structs` type and its `TrezorUiEnum` variant, an
// arm in core's dispatch, and the layout's function here. Every layout goes
// through `UiV1::ui_call`: a `data` field is pulled by core from the app's
// slice until P10 lands.
//
// ButtonRequests: the app names the step and nothing else. Core prefixes the
// app's identity, its image ID (`testapp.trezor.io`), and adds the `/menu` and
// `/details` suffixes, the `ButtonRequestType` (always `Other`), page counts,
// and whether a repeat is a new step.
//
// Layout: the public surface is this file plus one private module per layout
// (`review`, `decision`, `verify`, `done`, `progress`) and one for the facts
// they show (`field`). A public file holds only what an app may use — the
// layout's function and the types an app names — so that reading a public file
// is reading the API.
//
// A layout file is dull on purpose: arguments in, one answer out, the wire
// call in between. Anything cleverer belongs in the firmware, not here.
// Each layout's own example lives on its function, where rustdoc shows it; the
// private modules' `//!` docs are for maintainers. The re-exports below are
// grouped by rustfmt (`group_imports`), so do not try to arrange them by hand.
mod call;
mod decision;
mod done;
mod field;
mod progress;
mod review;
mod verify;

pub use decision::{Details, danger, details};
pub use done::done;
pub use field::Field;
pub use progress::{Progress, progress};
pub use review::{Review, review};
pub use verify::{verify_address, verify_pubkey};

//! The app↔core UI message.
//!
//! Compiled into both sides: the app builds these, the dispatcher decodes them.
//! This is the whole vocabulary the untrusted side has for asking that
//! something be shown, so what is *absent* matters as much as what is present.
//!
//! Absent on purpose, because the trusted side derives them from the block:
//! the confirm gesture and whether it is held, button labels, back-navigation,
//! severity styling, address chunking, page counts, and the ButtonRequest that
//! announces the screen to the host. An app chooses *which* block to show and
//! *what facts* go on it — never how the device presents them.
//!
//! # Menus
//!
//! A menu mirrors what `trezor.ui.layouts.menu` can already do — submenus and
//! property pages that resume the menu — with one difference: a leaf that would run app
//! code cannot carry a closure across
//! IPC. Instead the app keeps its callbacks, only the *shape* is serialized,
//! and a chosen leaf comes back as [`UiOutcome::Menu`] naming which one. The
//! SDK looks the callback up and runs it, so the app still sees one blocking
//! call and one answer.
//!
//! A callback returns `Option<UiOutcome>`, which is the same signal Python uses
//! and for the same reason: `Some(_)` means a decision was reached and the
//! block is over, `None` means nothing was decided, so the menu reopens and
//! keeps asking. Because the block's own outcome is a closed two-variant enum,
//! a callback cannot invent a third answer — and unlike Python's `R | None`,
//! the resume sentinel here can never collide with a legitimate value.
//!
//! There is deliberately no "cancel" entry kind. Cancelling is already one of
//! the outcomes every block can produce, so an entry that abandons the block is
//! just a callback returning `Some(UiOutcome::Cancelled)` — and whether that
//! needs confirming first is then the app's composition rather than a special
//! case in here. Python's `cancel_leaf(confirm=...)` becomes an ordinary
//! callback that shows a confirm block and decides.
//!
//! Resuming costs a round trip: core keeps no session (its loop is sequential
//! and cannot service a UI call while a menu is open), so the menu is re-sent
//! with [`UiRequest::open_at`] to reopen where the user was.
//!
//! The tree is stored **flat**: rkyv cannot archive a self-referential borrowed
//! type (`Slice<'a, MenuItem<'a>>` inside `MenuItem` is infinite trait
//! recursion), so a submenu names a contiguous run of children instead of
//! owning them. That turns out to be the better wire anyway — an item's
//! identity is a single index, so "coordinates" are one `u16`, validated with a
//! bounds check, and the app's callbacks live in a parallel array under the
//! same indices.

// Every type here is documented; its fields are not. They are wire fields whose
// names are the documentation — `title`, `props`, `value` — and restating them
// one by one would bury the parts that do carry meaning.
#![allow(missing_docs)]

use rkyv::{Archive, Deserialize, Serialize};
use ufmt::derive::uDebug;

use crate::structs::{Property, Slice, StrSlice};

// ============================================================================
// Data types
// ============================================================================

/// What a value is, which is what decides how it is formatted.
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize, Deserialize)]
pub enum ValueKind {
    /// Shown as written.
    Text,
    /// Grouped into chunks so it can be compared by eye.
    Address,
    /// Opaque bytes as hex, paged by the renderer.
    Data,
}

/// A note along the bottom of a screen.
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize)]
pub enum Footer<'a> {
    /// Ordinary guidance.
    Hint(StrSlice<'a>),
    /// Something to weigh before confirming.
    Warning(StrSlice<'a>),
}

/// How much alarm a notice carries.
///
/// The app picks it — it always could, by picking which function to call — but
/// what a severity looks like, and what gesture it demands, follow from it.
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize, Deserialize)]
pub enum Severity {
    /// Worth reading; dismissible.
    Info,
    /// Worth pausing over.
    Warning,
    /// Must be acknowledged deliberately.
    Danger,
}

/// A labelled amount, as shown on a summary.
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize)]
pub struct Amount<'a> {
    pub label: StrSlice<'a>,
    pub value: StrSlice<'a>,
}

/// How an entry should look, mirroring `trezorui_api.MenuItemIntent`.
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize, Deserialize)]
pub enum MenuIntent {
    /// An ordinary entry.
    Standard,
    /// An entry that should read as consequential.
    Danger,
}

/// What choosing an entry does.
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize)]
pub enum MenuAction<'a> {
    /// Opens a submenu: a contiguous run of [`Menu::items`].
    Submenu { first: u16, count: u16 },
    /// Shows a page of key/value facts and then returns to the menu — the
    /// analogue of a Python leaf that yields `None`.
    Properties { props: Slice<'a, Property<'a>> },
    /// Leaves the menu and reports this entry's index, so the app can run the
    /// callback it kept for it.
    ///
    /// This covers everything a menu entry can do beyond showing facts,
    /// including abandoning the block: the callback simply returns
    /// `Some(UiOutcome::Cancelled)`.
    Callback,
}

/// One entry in a menu.
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize)]
pub struct MenuItem<'a> {
    pub title: StrSlice<'a>,
    pub intent: MenuIntent,
    pub action: MenuAction<'a>,
    /// Index of the entry whose submenu holds this one; `u16::MAX` at the root.
    ///
    /// Only needed to reopen a menu at a given entry without walking the whole
    /// tree to find which level it belongs to.
    pub parent: u16,
}

/// A menu, flattened.
///
/// `items[..root_count]` is the top level; deeper levels are the runs named by
/// [`MenuAction::Submenu`]. Every index the dispatcher follows is bounds-checked
/// against `items`, so a malformed tree is a protocol error rather than a
/// crash.
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize)]
pub struct Menu<'a> {
    pub items: Slice<'a, MenuItem<'a>>,
    pub root_count: u16,
}

/// What the user is being asked about.
///
/// One variant per block. The dispatcher matches on this to derive everything
/// the message deliberately does not carry.
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize)]
pub enum Block<'a> {
    /// A generic yes/no.
    ConfirmAction {
        title: StrSlice<'a>,
        action: StrSlice<'a>,
        description: Option<StrSlice<'a>>,
        subtitle: Option<StrSlice<'a>>,
    },
    /// One value, formatted according to its kind. Long values are paged by the
    /// renderer, the only side that knows what fits.
    ConfirmValue {
        title: StrSlice<'a>,
        value: StrSlice<'a>,
        kind: ValueKind,
        subtitle: Option<StrSlice<'a>>,
        description: Option<StrSlice<'a>>,
        footer: Option<Footer<'a>>,
    },
    /// A list of key/value facts.
    ConfirmProperties {
        title: StrSlice<'a>,
        props: Slice<'a, Property<'a>>,
        subtitle: Option<StrSlice<'a>>,
    },
    /// The closing screen of a transaction.
    ConfirmSummary {
        title: StrSlice<'a>,
        amount: Option<Amount<'a>>,
        fee: Option<Amount<'a>>,
    },
    /// Something the user should know, at one of three levels of alarm.
    ShowNotice {
        severity: Severity,
        title: StrSlice<'a>,
        content: StrSlice<'a>,
    },
    /// Something finished. Says nothing about whether anything was signed.
    ShowSuccess {
        title: StrSlice<'a>,
        content: StrSlice<'a>,
    },
    /// An address to check, with its QR.
    ShowAddress {
        address: StrSlice<'a>,
        subtitle: Option<StrSlice<'a>>,
    },
}

/// One action: a block, plus the menu any block may offer behind its menu
/// button.
///
/// The menu sits beside the block rather than inside it because every block can
/// have one, and because it lets the dispatcher build menus in one place rather
/// than once per variant. An empty `items` means no menu button.
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize)]
pub struct UiRequest<'a> {
    pub block: Block<'a>,
    pub menu: Menu<'a>,
    /// Reopen the menu with this entry highlighted, instead of showing the
    /// block's main screen.
    ///
    /// Set by the SDK when a callback returned `None`, so that resuming looks
    /// like returning rather than starting over. Bounds-checked like any other
    /// index.
    pub open_at: Option<u16>,
}

/// What the user did.
///
/// Three-valued on the wire, two-valued to the app: the SDK consumes
/// [`UiOutcome::Menu`] by running the callback it kept, so a block is still one
/// blocking call and one answer.
///
/// There is no `Back` and no `Info`: sequences run forward, and a menu is
/// walked inside the block rather than reported out of it.
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize, Deserialize)]
pub enum UiOutcome {
    /// The user confirmed.
    Confirmed,
    /// The user left without confirming.
    Cancelled,
    /// A [`MenuAction::Callback`] entry was chosen; the index says which.
    Menu(u16),
}

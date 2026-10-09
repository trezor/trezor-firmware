//! Low-level IPC message types for the Trezor UI, Crypto, and Progress interfaces.
//!
//! These types are serialized via [`rkyv`] and sent over IPC between the app
//! and the Core firmware task.
//!
//! Apps use `modui` and `crypto`, not these. Fields are `pub` because core
//! reads them straight off the archived (rkyv) form.

use rkyv::boxed::{ArchivedBox, BoxResolver};
use rkyv::option::ArchivedOption;
use rkyv::rancor::Fallible;
use rkyv::ser::Writer;
use rkyv::{Archive, Deserialize, Place, Serialize, SerializeUnsized};
use stabby::IStable;
use stabby::slice::Slice as StabbySlice;
use stabby::str::Str;
use ufmt::derive::uDebug;

/// A key-value pair with an optional monospace flag, used in UI detail views.
#[stabby::stabby]
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize)]
pub struct Property<'a> {
    /// The label, such as `"Amount"`.
    pub key: StrSlice<'a>,
    /// The content shown under the label.
    pub value: StrSlice<'a>,
    /// Whether the value is shown in a fixed-width font.
    pub mono: bool,
}

impl<'a> Property<'a> {
    /// A fact with `key` as its label and `value` as its content. `mono` shows
    /// the value in a fixed-width font; prefer [`Property::plain`] or
    /// [`Property::mono`], which say which.
    pub fn new(key: &'a str, value: &'a str, mono: bool) -> Self {
        Self {
            key: key.into(),
            value: value.into(),
            mono,
        }
    }

    /// A fact whose value is machine-like — a hash, a hex string — and reads
    /// better in a fixed-width font.
    pub fn mono(key: &'a str, value: &'a str) -> Self {
        Self::new(key, value, true)
    }

    /// A fact whose value is ordinary text.
    pub fn plain(key: &'a str, value: &'a str) -> Self {
        Self::new(key, value, false)
    }
}

// ============================================================================
// Field types
// ============================================================================
//
// Every request type below is both `#[stabby::stabby]` and rkyv `Archive`: an
// app passes it through the `UiV1` vtable as-is, and `core/embed/api`
// serializes that same value for IPC. These three field types make that work:
// each holds stabby's FFI-safe form and archives as the rkyv type core reads.

/// A borrowed string: stabby `Str` across the FFI, `ArchivedBox<str>` on the
/// wire.
#[stabby::stabby]
#[derive(Copy, Clone, PartialEq, Eq)]
pub struct StrSlice<'a> {
    inner: Str<'a>,
}

impl<'a> StrSlice<'a> {
    pub const fn new(s: &'a str) -> Self {
        Self { inner: Str::new(s) }
    }

    pub fn as_str(&self) -> &'a str {
        self.inner.as_str()
    }
}

// ufmt deliberately doesn't implement uDebug for `str`, so this writes the raw
// contents, matching ufmt's own `uDisplay for str`.
impl<'a> ufmt::uDebug for StrSlice<'a> {
    fn fmt<W: ?Sized>(&self, f: &mut ufmt::Formatter<'_, W>) -> Result<(), W::Error>
    where
        W: ufmt::uWrite,
    {
        f.write_str(self.as_str())
    }
}

impl<'a> From<&'a str> for StrSlice<'a> {
    fn from(s: &'a str) -> Self {
        Self::new(s)
    }
}

// Archives as rkyv's own `ArchivedBox<str>`, which carries a correct
// CheckBytes impl, so core reads it through validated `rkyv::access`.
impl<'a> Archive for StrSlice<'a> {
    type Archived = ArchivedBox<str>;
    type Resolver = BoxResolver;

    fn resolve(&self, resolver: Self::Resolver, out: Place<Self::Archived>) {
        ArchivedBox::resolve_from_ref(self.as_str(), resolver, out)
    }
}

impl<'a, S: Fallible + Writer + ?Sized> Serialize<S> for StrSlice<'a> {
    fn serialize(&self, serializer: &mut S) -> Result<Self::Resolver, S::Error> {
        ArchivedBox::serialize_from_ref(self.as_str(), serializer)
    }
}

/// An optional borrowed string. Archives exactly as `Option<StrSlice>` would.
///
/// Not a stabby `Option<Str>`: stabby cannot niche that, and its `Option`
/// is not `Copy`. A flag next to the bytes is both.
#[stabby::stabby]
#[derive(Copy, Clone, PartialEq, Eq)]
pub struct OptStrSlice<'a> {
    inner: Str<'a>,
    some: bool,
}

impl<'a> OptStrSlice<'a> {
    pub const NONE: Self = Self {
        inner: Str::new(""),
        some: false,
    };

    pub const fn new(s: Option<&'a str>) -> Self {
        match s {
            Some(s) => Self {
                inner: Str::new(s),
                some: true,
            },
            None => Self::NONE,
        }
    }

    pub fn as_str(&self) -> Option<&'a str> {
        self.some.then(|| self.inner.as_str())
    }

    fn as_slice(&self) -> Option<StrSlice<'a>> {
        self.as_str().map(StrSlice::new)
    }
}

impl<'a> ufmt::uDebug for OptStrSlice<'a> {
    fn fmt<W: ?Sized>(&self, f: &mut ufmt::Formatter<'_, W>) -> Result<(), W::Error>
    where
        W: ufmt::uWrite,
    {
        self.as_slice().fmt(f)
    }
}

impl<'a> From<Option<&'a str>> for OptStrSlice<'a> {
    fn from(s: Option<&'a str>) -> Self {
        Self::new(s)
    }
}

impl<'a> Archive for OptStrSlice<'a> {
    type Archived = ArchivedOption<ArchivedBox<str>>;
    type Resolver = Option<BoxResolver>;

    fn resolve(&self, resolver: Self::Resolver, out: Place<Self::Archived>) {
        self.as_slice().resolve(resolver, out)
    }
}

impl<'a, S: Fallible + Writer + ?Sized> Serialize<S> for OptStrSlice<'a> {
    fn serialize(&self, serializer: &mut S) -> Result<Self::Resolver, S::Error> {
        self.as_slice().serialize(serializer)
    }
}

/// A borrowed slice: stabby `Slice` across the FFI, `ArchivedBox<[T]>` on the
/// wire.
#[stabby::stabby]
pub struct Slice<'a, T: IStable> {
    inner: StabbySlice<'a, T>,
}

// Manual Copy/Clone: only the borrow is copied, never the elements.
impl<'a, T: IStable> Copy for Slice<'a, T> {}

impl<'a, T: IStable> Clone for Slice<'a, T> {
    fn clone(&self) -> Self {
        *self
    }
}

impl<'a, T: IStable + ufmt::uDebug> ufmt::uDebug for Slice<'a, T> {
    fn fmt<W: ?Sized>(&self, f: &mut ufmt::Formatter<'_, W>) -> Result<(), W::Error>
    where
        W: ufmt::uWrite,
    {
        self.as_slice().fmt(f)
    }
}

impl<'a, T: IStable + PartialEq> PartialEq for Slice<'a, T> {
    fn eq(&self, other: &Self) -> bool {
        self.as_slice() == other.as_slice()
    }
}

impl<'a, T: IStable + Eq> Eq for Slice<'a, T> {}

impl<'a, T: IStable> Slice<'a, T> {
    pub fn new(s: &'a [T]) -> Self {
        Self { inner: s.into() }
    }

    pub fn as_slice(&self) -> &'a [T] {
        let inner = self.inner;
        // SAFETY: `inner` borrows `'a` data; `Slice::as_slice` only ties the
        // result to `&self`, so this restores the original lifetime.
        unsafe { core::slice::from_raw_parts(inner.as_slice().as_ptr(), inner.len()) }
    }

    pub fn len(&self) -> usize {
        self.inner.len()
    }

    pub fn is_empty(&self) -> bool {
        self.inner.is_empty()
    }
}

impl<'a, T: IStable> From<&'a [T]> for Slice<'a, T> {
    fn from(s: &'a [T]) -> Self {
        Self::new(s)
    }
}

// Archives as rkyv's own `ArchivedBox<[T::Archived]>`, for the same reason as
// `StrSlice`.
impl<'a, T: IStable + Archive> Archive for Slice<'a, T> {
    type Archived = ArchivedBox<[T::Archived]>;
    type Resolver = BoxResolver;

    fn resolve(&self, resolver: Self::Resolver, out: Place<Self::Archived>) {
        ArchivedBox::resolve_from_ref(self.as_slice(), resolver, out)
    }
}

impl<'a, T: IStable + Archive, S: Fallible + Writer + ?Sized> Serialize<S> for Slice<'a, T>
where
    [T]: SerializeUnsized<S>,
{
    fn serialize(&self, serializer: &mut S) -> Result<Self::Resolver, S::Error> {
        ArchivedBox::serialize_from_ref(self.as_slice(), serializer)
    }
}

/// More the person can look at from a block's screen: an entry in the block's
/// menu, and the facts shown when it is picked.
///
/// Travels with the block's request; core walks the menu itself and answers
/// the app only when the block is decided.
#[stabby::stabby]
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize)]
pub struct ExtraItem<'a> {
    /// The menu entry's label, and the title of its screen.
    pub label: StrSlice<'a>,
    pub props: Slice<'a, Property<'a>>,
}

/// What confirming a block commits the person to.
///
/// The app knows which of its screens is the one that signs; the library does
/// not. The app says so here, and core turns it into the gesture — a hold
/// rather than a tap — so the person's last yes is harder to give by accident.
/// The gesture itself is not the app's to name.
///
/// WIP: on caesar a screen with extras has a menu instead of the hold, so
/// `Final` is a tap there (#7694).
#[stabby::stabby]
#[repr(u8)]
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize)]
pub enum Commitment {
    /// One step of a longer flow. Confirming it only moves on.
    Step,
    /// The last confirmation before the app signs or otherwise acts.
    Final,
}

/// An action confirmation screen, sent as [`TrezorUiEnum::ConfirmAction`].
#[stabby::stabby]
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize)]
pub struct ConfirmAction<'a> {
    pub title: StrSlice<'a>,
    pub action: StrSlice<'a>,
    pub description: OptStrSlice<'a>,
    pub subtitle: OptStrSlice<'a>,
    pub commitment: Commitment,
    /// The step's name, announced to the host.
    pub br_name: StrSlice<'a>,
    /// Reached from the screen's menu button, which core draws when there
    /// are any.
    pub extras: Slice<'a, ExtraItem<'a>>,
}

/// A transaction summary, sent as [`TrezorUiEnum::ConfirmSummary`].
#[stabby::stabby]
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize)]
pub struct ConfirmSummary<'a> {
    pub title: StrSlice<'a>,
    pub amount: OptStrSlice<'a>,
    pub amount_label: OptStrSlice<'a>,
    pub fee: StrSlice<'a>,
    pub fee_label: StrSlice<'a>,
    /// The step's name, announced to the host.
    pub br_name: StrSlice<'a>,
    /// Reached from the screen's menu button, which core draws when there
    /// are any.
    pub extras: Slice<'a, ExtraItem<'a>>,
}

/// What a value *is*, which decides how it is formatted.
///
/// There is deliberately no `chunkify` flag: grouping an address into chunks
/// is a consequence of it being an address, not a separate choice.
#[stabby::stabby]
#[repr(u8)]
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize)]
pub enum ValueKind {
    /// Shown as written.
    Text,
    /// Grouped into chunks so it can be compared by eye.
    Address,
    /// Raw bytes as hex, paged with a counter; what `confirm::data` sends.
    Data,
}

/// A value confirmation screen, sent as [`TrezorUiEnum::ConfirmValue`].
#[stabby::stabby]
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize)]
pub struct ConfirmValue<'a> {
    pub title: StrSlice<'a>,
    pub value: StrSlice<'a>,
    pub kind: ValueKind,
    pub subtitle: OptStrSlice<'a>,
    pub description: OptStrSlice<'a>,
    /// A note along the bottom of the screen.
    pub footer: OptStrSlice<'a>,
    /// Whether the note is something to weigh before confirming.
    pub footer_warning: bool,
    pub commitment: Commitment,
    /// The step's name, announced to the host.
    pub br_name: StrSlice<'a>,
    /// Reached from the screen's menu button, which core draws when there
    /// are any.
    pub extras: Slice<'a, ExtraItem<'a>>,
}

/// What kind of news a notice is.
///
/// The only thing the app decides about a notice. The screen, its button words
/// and its timeout follow from it, and are core's, per model — which is why
/// this travels as a meaning rather than as a look.
///
/// There is no error severity, on purpose. A failure is not a notice a flow
/// carries on from: an app fails by returning `Err`, and whether the person
/// sees a screen for that is core's to decide on the failure path, as
/// `show_error_and_raise` does for core's own flows.
#[stabby::stabby]
#[repr(u8)]
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize)]
pub enum Severity {
    /// A step worked, and the flow continues after this screen.
    ///
    /// For example a signature that verified. Distinct from
    /// [`Severity::Done`], which is the last screen of a flow.
    Success,
    /// The flow finished; the person goes back to the host.
    ///
    /// The last screen an app shows. Nothing on the device follows it, so
    /// the call does not wait for the person to dismiss it — the host's
    /// response should not wait on an acknowledgement. What the screen does
    /// after the call returns is the model's business.
    ///
    /// WIP: bolt and caesar wait for a tap.
    Done,
    /// Something to read before going on. Nothing is at stake.
    Info,
    /// Something to consider before going on.
    Warning,
    /// Going on is risky; the person has to choose it deliberately.
    Danger,
}

/// A notice of some [`Severity`], sent as [`TrezorUiEnum::ShowNotice`].
///
/// Carries what the notice says and nothing about how it looks: no button
/// words, no timeout, no choice of screen. Core derives those from `severity`.
#[stabby::stabby]
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize)]
pub struct ShowNotice<'a> {
    pub severity: Severity,
    pub title: StrSlice<'a>,
    pub content: StrSlice<'a>,
    /// Reached from the screen's menu button, which core draws when there
    /// are any.
    pub extras: Slice<'a, ExtraItem<'a>>,
    /// The notice must offer a way to back out. How is the model's.
    /// WIP: ignored by every model.
    pub cancel: bool,
    /// The step's name, announced to the host.
    pub br_name: StrSlice<'a>,
}

/// A property-list confirmation, sent as [`TrezorUiEnum::ConfirmProperties`].
#[stabby::stabby]
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize)]
pub struct ConfirmProperties<'a> {
    pub title: StrSlice<'a>,
    pub props: Slice<'a, Property<'a>>,
    pub subtitle: OptStrSlice<'a>,
    pub commitment: Commitment,
    /// The step's name, announced to the host.
    pub br_name: StrSlice<'a>,
    /// Reached from the screen's menu button, which core draws when there
    /// are any.
    pub extras: Slice<'a, ExtraItem<'a>>,
}

/// One UI request, as it crosses IPC: one variant per `modui` block.
/// `core/embed/api` wraps the request the app passed through the `UiV1` vtable
/// and serializes it.
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize)]
pub enum TrezorUiEnum<'a> {
    ConfirmAction(ConfirmAction<'a>),
    ConfirmSummary(ConfirmSummary<'a>),
    ConfirmValue(ConfirmValue<'a>),
    ConfirmProperties(ConfirmProperties<'a>),
    ShowNotice(ShowNotice<'a>),
}

/// What the person did with one screen. Written by core, read by `modui`;
/// apps never see it.
///
/// Variants say what the person *did*, not which button did it. Only the
/// block's final answer crosses: what happens in its menu stays in core.
#[must_use]
#[stabby::stabby]
#[repr(u8)]
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize, Deserialize)]
pub enum UiReply {
    /// Yes, having seen all of it.
    ///
    /// WIP: until chunk paging exists, every chunk of `confirm::data` answers
    /// this too.
    Confirmed,
    /// Refused, or left without answering. `modui` turns it into
    /// `Err(Error::Cancelled)`.
    Cancelled,
    // WIP: chunk paging. No screen produces these yet; they come back with it.
    // /// Paged past the end of the content core holds; the sender has more.
    // Forward,
    // /// Paged back before the content core holds.
    // Backward,
    // /// Accepted the rest without reading it (on the screen or in the menu;
    // /// undecided).
    // ConfirmedAll,
}

/// All crypto operations that can be requested from the app via IPC.
///
/// Constructed by the higher-level `crypto` module — do not construct variants directly.
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize)]
pub enum TrezorCryptoEnum<'a> {
    GetXpub {
        address_n: Slice<'a, u32>,
        xpub_magic: u32,
    },
    GetPublicKey {
        address_n: Slice<'a, u32>,
        compressed: bool,
    },
    SignDigest {
        address_n: Slice<'a, u32>,
        digest: [u8; 32],
        compressed: bool,
    },
    SignTypedHash {
        address_n: Slice<'a, u32>,
        hash: [u8; 32],
        encoded_network: Option<Slice<'a, u8>>,
        encoded_token: Option<Slice<'a, u8>>,
        chain_id: Option<u64>,
        show_progress: bool,
    },
    GetAddressMac {
        address_n: Slice<'a, u32>,
        address: StrSlice<'a>,
    },
    CheckAddressMac {
        address_n: Slice<'a, u32>,
        mac: [u8; 32],
        address: StrSlice<'a>,
    },
    VerifyNonceCache {
        nonce: Slice<'a, u8>,
    },
}

impl<'a> TrezorCryptoEnum<'a> {
    pub fn id(&self) -> u8 {
        match self {
            Self::GetXpub { .. } => 0,
            Self::GetPublicKey { .. } => 1,
            Self::SignDigest { .. } => 2,
            Self::SignTypedHash { .. } => 3,
            Self::GetAddressMac { .. } => 4,
            Self::CheckAddressMac { .. } => 5,
            Self::VerifyNonceCache { .. } => 6,
        }
    }
}

/// Result returned by the Core task after a crypto operation, borrowed
/// directly from the archived IPC buffer.
///
/// See [`TrezorCryptoResult`] for the owned, app-facing equivalent.
#[derive(Copy, Clone, PartialEq, Eq, Archive, Serialize, Deserialize)]
pub enum TrezorCryptoResultRef<'a> {
    Xpub([u8; 111]),
    PublicKey(Slice<'a, u8>), // 32, 33 or 65 bytes depending on the curve
    Signature([u8; 65]),
    AddressMac([u8; 32]),
    Boolean(bool),
}

// Manual uDebug: `[u8; 111]`/`[u8; 65]` are too long for ufmt's built-in
// fixed-size-array uDebug impls (only implemented up to length 32), so the
// large byte arrays are debug-printed as slices instead.
impl<'a> ufmt::uDebug for TrezorCryptoResultRef<'a> {
    fn fmt<W: ?Sized>(&self, f: &mut ufmt::Formatter<'_, W>) -> Result<(), W::Error>
    where
        W: ufmt::uWrite,
    {
        match self {
            Self::Xpub(xpub) => f.debug_tuple("Xpub")?.field(&&xpub[..])?.finish(),
            Self::PublicKey(key) => f.debug_tuple("PublicKey")?.field(key)?.finish(),
            Self::Signature(sig) => f.debug_tuple("Signature")?.field(&&sig[..])?.finish(),
            Self::AddressMac(mac) => f.debug_tuple("AddressMac")?.field(mac)?.finish(),
            Self::Boolean(b) => f.debug_tuple("Boolean")?.field(b)?.finish(),
        }
    }
}

/// Owned result of a crypto operation, returned by the `crypto` module's
/// public functions.
///
/// See [`TrezorCryptoResultRef`] for the borrowed, wire-level equivalent.
#[derive(Clone, PartialEq, Eq)]
#[cfg(feature = "app")]
pub enum TrezorCryptoResult {
    XpubBytes([u8; 33]),
    Signature([u8; 65]),
    AddressMac([u8; 32]),
    Boolean(bool),
}

#[cfg(feature = "app")]
impl ufmt::uDebug for TrezorCryptoResult {
    fn fmt<W: ?Sized>(&self, f: &mut ufmt::Formatter<'_, W>) -> Result<(), W::Error>
    where
        W: ufmt::uWrite,
    {
        match self {
            Self::XpubBytes(xpub) => f.debug_tuple("XpubBytes")?.field(&&xpub[..])?.finish(),
            Self::Signature(sig) => f.debug_tuple("Signature")?.field(&&sig[..])?.finish(),
            Self::AddressMac(mac) => f.debug_tuple("AddressMac")?.field(mac)?.finish(),
            Self::Boolean(b) => f.debug_tuple("Boolean")?.field(b)?.finish(),
        }
    }
}

/// Progress bar operations that can be requested from the app via IPC.
///
/// Built by `core/embed/api`; apps use `modui::progress`.
///
/// The three variants are one lifecycle: `Init` opens the progress, `Update`
/// moves its fill — 0 to 1000, which the app SDK computes; core only draws —
/// and `End` closes it. The app SDK pairs them with a guard that sends `End`
/// on drop, so an app cannot leave a progress on screen for work that
/// stopped; see the `modui` progress docs.
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize, Deserialize)]
pub enum TrezorProgressEnum<'a> {
    Init {
        description: OptStrSlice<'a>,
        title: OptStrSlice<'a>,
        indeterminate: bool,
        danger: bool,
    },
    Update {
        description: OptStrSlice<'a>,
        /// How far along, from 0 to 1000.
        value: u32,
    },
    End,
}

impl<'a> TrezorProgressEnum<'a> {
    pub fn id(&self) -> u16 {
        match self {
            TrezorProgressEnum::Init { .. } => 0,
            TrezorProgressEnum::Update { .. } => 1,
            TrezorProgressEnum::End => 2,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Ensures every variant of TrezorCryptoEnum has a unique id()
    /// and that no variant is accidentally forgotten.
    #[test]
    fn crypto_ids_are_unique_and_exhaustive() {
        use TrezorCryptoEnum::*;
        let empty_u32: &[u32] = &[];
        let empty_u8: &[u8] = &[];
        let variants: &[(u8, &str)] = &[
            (
                GetXpub {
                    address_n: empty_u32.into(),
                    xpub_magic: 0,
                }
                .id(),
                "GetXpub",
            ),
            (
                GetPublicKey {
                    address_n: empty_u32.into(),
                    compressed: false,
                }
                .id(),
                "GetPublicKey",
            ),
            (
                SignDigest {
                    address_n: empty_u32.into(),
                    digest: [0u8; 32],
                    compressed: false,
                }
                .id(),
                "SignDigest",
            ),
            (
                SignTypedHash {
                    address_n: empty_u32.into(),
                    hash: [0u8; 32],
                    encoded_network: None,
                    encoded_token: None,
                    chain_id: None,
                    show_progress: false,
                }
                .id(),
                "SignTypedHash",
            ),
            (
                GetAddressMac {
                    address_n: empty_u32.into(),
                    address: "".into(),
                }
                .id(),
                "GetAddressMac",
            ),
            (
                CheckAddressMac {
                    address_n: empty_u32.into(),
                    mac: [0u8; 32],
                    address: "".into(),
                }
                .id(),
                "CheckAddressMac",
            ),
            (
                VerifyNonceCache {
                    nonce: empty_u8.into(),
                }
                .id(),
                "VerifyNonceCache",
            ),
        ];
        let mut seen = std::collections::HashSet::new();
        for (id, name) in variants {
            assert!(seen.insert(id), "duplicate id {} for variant {}", id, name);
        }
        assert_eq!(variants.len(), 7, "new variant added but test not updated");
    }

    /// Ensures every variant of TrezorProgressEnum has a unique id()
    /// and that no variant is accidentally forgotten.
    #[test]
    fn progress_ids_are_unique_and_exhaustive() {
        use TrezorProgressEnum::*;
        let variants: &[(u16, &str)] = &[
            (
                Init {
                    description: None,
                    title: None,
                    indeterminate: false,
                    danger: false,
                }
                .id(),
                "Init",
            ),
            (
                Update {
                    description: None,
                    value: 0,
                }
                .id(),
                "Update",
            ),
            (End.id(), "End"),
        ];
        // all IDs must be unique
        let mut seen = std::collections::HashSet::new();
        for (id, name) in variants {
            assert!(seen.insert(id), "duplicate id {} for variant {}", id, name);
        }
        // total count must match — add new variants here when extending the enum
        assert_eq!(variants.len(), 3, "new variant added but test not updated");
    }
}

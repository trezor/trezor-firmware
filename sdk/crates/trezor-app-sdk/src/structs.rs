//! The requests an app sends to core, and core's replies, for the UI, crypto
//! and progress services.
//!
//! Each type is serialized with [`rkyv`] and sent over IPC between the app and
//! the core task. A UI request is also what the app builds: `modui`'s params
//! types are these, under their own names. Fields are `pub` because core reads
//! them straight off the archived form.
//!
//! The UI types also cross the `UiV1` vtable by value, between an app and a
//! firmware that are built apart, so their layout is the app ABI. That is why
//! the UI enums number their variants explicitly: within one API version a
//! new variant goes at the end with a new value, and no value is ever
//! renumbered or reused.

use rkyv::boxed::{ArchivedBox, BoxResolver};
use rkyv::option::ArchivedOption;
use rkyv::rancor::Fallible;
use rkyv::ser::Writer;
use rkyv::{Archive, Deserialize, Place, Serialize, SerializeUnsized};
use stabby::IStable;
use stabby::slice::Slice as StabbySlice;
use stabby::str::Str;
use ufmt::derive::uDebug;

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

// Archives as rkyv's own `ArchivedBox<str>`, whose `CheckBytes` core can use
// to validate a request (WIP: core reads it with `access_unchecked`).
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

/// What a fact *is*, which decides how core formats and draws it.
///
/// The app chooses the kind by what the value is, never by how it should look.
/// The discriminants are the wire's (contract C1): a new kind goes at the end
/// with a new value, and no value is ever renumbered or reused.
#[stabby::stabby]
#[repr(u8)]
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize)]
pub enum FieldKind {
    /// Words or a number, shown as written.
    Text = 0,
    /// A sum with its unit, already formatted by the app.
    Amount = 1,
    /// Something compared character by character: grouped and fixed-width.
    Address = 2,
    /// Raw bytes, shown as hex. At most one per review.
    Data = 3,
    /// A sentence with no label: a question or an explanation.
    Note = 4,
    /// A sentence to weigh before confirming; a caution row.
    Warning = 5,
}

/// One fact in a [`ReviewRequest`] or [`FieldsRequest`].
///
/// `label` is `None` for [`FieldKind::Note`] and [`FieldKind::Warning`].
/// `value` is UTF-8 for the text kinds and the bytes themselves for
/// [`FieldKind::Data`]. `len` is `value.len()`; for `Data` after P10 it is the
/// total length core pulls, and the value travels empty.
#[stabby::stabby]
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize)]
pub struct WireField<'a> {
    pub kind: FieldKind,
    pub label: OptStrSlice<'a>,
    pub value: Slice<'a, u8>,
    pub len: u32,
}

/// More the person can open from a review's menu: the entry's label, and the
/// facts shown when it is picked.
#[stabby::stabby]
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize)]
pub struct WireExtra<'a> {
    pub label: StrSlice<'a>,
    pub fields: Slice<'a, WireField<'a>>,
}

/// Facts for the person to confirm or refuse, sent as
/// [`TrezorUiEnum::Review`].
#[stabby::stabby]
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize)]
pub struct ReviewRequest<'a> {
    pub step: StrSlice<'a>,
    pub title: StrSlice<'a>,
    pub fields: Slice<'a, WireField<'a>>,
    pub extras: Slice<'a, WireExtra<'a>>,
    /// The last yes before the app signs or acts: core makes it a hold.
    pub is_final: bool,
}

/// A risky decision, sent as [`TrezorUiEnum::Danger`].
#[stabby::stabby]
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize)]
pub struct FieldsRequest<'a> {
    pub step: StrSlice<'a>,
    pub title: StrSlice<'a>,
    pub fields: Slice<'a, WireField<'a>>,
}

/// An address or public key of the person's own, sent as
/// [`TrezorUiEnum::VerifyAddress`] or [`TrezorUiEnum::VerifyPubkey`].
#[stabby::stabby]
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize)]
pub struct VerifyRequest<'a> {
    pub step: StrSlice<'a>,
    pub value: StrSlice<'a>,
    pub account: OptStrSlice<'a>,
    pub path: OptStrSlice<'a>,
}

/// The end of a flow, sent as [`TrezorUiEnum::Done`].
#[stabby::stabby]
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize)]
pub struct DoneRequest<'a> {
    pub step: StrSlice<'a>,
    pub text: StrSlice<'a>,
}

/// One UI request, as it crosses IPC: one variant per decision an app asks.
///
/// The discriminants are the wire's (contract C1): a new variant goes at the end
/// with a new value, and no value is ever renumbered or reused.
#[stabby::stabby]
#[repr(C, u8)]
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize)]
pub enum TrezorUiEnum<'a> {
    Review(ReviewRequest<'a>) = 0,
    Danger(FieldsRequest<'a>) = 1,
    Details(FieldsRequest<'a>) = 2,
    VerifyAddress(VerifyRequest<'a>) = 3,
    VerifyPubkey(VerifyRequest<'a>) = 4,
    Done(DoneRequest<'a>) = 5,
}

/// How the person decided a request. Written by core, read by the app; apps
/// never see it.
///
/// Variants say what the person *did*, not which button did it. Only the
/// request's final answer crosses: what happens in its menu stays in core.
#[must_use]
#[stabby::stabby]
#[repr(u8)]
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize, Deserialize)]
pub enum TrezorUiResult {
    /// Confirmed.
    Confirmed = 0,
    /// Refused, or left without answering.
    Cancelled = 1,

    // Chunk paging, answers to a `Data` chunk only. The firmware's chunk loop
    // acts on them; `Forward` and `Backward` never reach the app.
    // WIP: P10 decides whether these survive the pulled-data protocol.
    /// Paged past the end of the chunk; the next chunk is wanted.
    Forward = 2,
    /// Paged back before the start of the chunk; the previous chunk is wanted.
    Backward = 3,
    /// Accepted the rest of the data without reading it.
    ConfirmedAll = 4,

    /// The person asked to see details.
    ShowDetails = 5,
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
    EcdsaSignDigest {
        address_n: Slice<'a, u32>,
        digest: [u8; 32],
        compressed: bool,
        /// A [`CanonicalSig`](crate::traits::crypto::CanonicalSig), as its
        /// `u8` value.
        canonical: u8,
    },
    Ed25519Sign {
        address_n: Slice<'a, u32>,
        message: Slice<'a, u8>,
    },
    GetAddressMac {
        address_n: Slice<'a, u32>,
        address: StrSlice<'a>,
        slip44: u32,
    },
    CheckAddressMac {
        address_n: Slice<'a, u32>,
        mac: [u8; 32],
        address: StrSlice<'a>,
        slip44: u32,
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
            Self::EcdsaSignDigest { .. } => 2,
            Self::Ed25519Sign { .. } => 3,
            Self::GetAddressMac { .. } => 4,
            Self::CheckAddressMac { .. } => 5,
            Self::VerifyNonceCache { .. } => 6,
        }
    }
}

/// Result of a crypto operation, sent by the Core task and borrowed directly
/// from the archived IPC buffer.
///
/// Deliberately generic: each caller knows which shape its operation returns,
/// and checks for it (including any fixed length) itself. Core reports a
/// failed operation as `Boolean(false)`, which no caller expecting data
/// accepts.
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize, Deserialize)]
pub enum TrezorCryptoResult<'a> {
    String(StrSlice<'a>),
    Bytes(Slice<'a, u8>),
    Boolean(bool),
}

/// Progress bar operations that can be requested from the app via IPC.
///
/// Built by `core/embed/api`; apps use `modui::progress`.
///
/// `Init` opens the progress, `Step` reports work done, `Label` changes the
/// text under the bar, and `End` closes it. Core keeps the count and turns it
/// into the bar. The app SDK pairs them with a guard that sends `End` on drop,
/// so an app cannot leave a progress on screen for work that stopped; see the
/// `modui` progress docs.
///
/// Only what the app chose travels; how the progress looks is core's.
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize, Deserialize)]
pub enum TrezorProgressEnum<'a> {
    Init {
        /// What the work is, such as `"Signing"`.
        label: StrSlice<'a>,
        /// How much work there is, in the app's own units. `0` means not
        /// known: the bar shows motion rather than a fill.
        total: u32,
    },
    Step {
        /// Units of work done since the last step.
        units: u32,
    },
    /// Changes the text under the bar while the work goes on.
    Label {
        /// What the work is now, such as `"Signing input 2/3"`.
        label: StrSlice<'a>,
    },
    End,
}

impl<'a> TrezorProgressEnum<'a> {
    pub fn id(&self) -> u16 {
        match self {
            TrezorProgressEnum::Init { .. } => 0,
            TrezorProgressEnum::Step { .. } => 1,
            TrezorProgressEnum::Label { .. } => 2,
            TrezorProgressEnum::End => 3,
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
                EcdsaSignDigest {
                    address_n: empty_u32.into(),
                    digest: [0u8; 32],
                    compressed: false,
                    canonical: 0,
                }
                .id(),
                "EcdsaSignDigest",
            ),
            (
                Ed25519Sign {
                    address_n: empty_u32.into(),
                    message: empty_u8.into(),
                }
                .id(),
                "Ed25519Sign",
            ),
            (
                GetAddressMac {
                    address_n: empty_u32.into(),
                    address: "".into(),
                    slip44: 0,
                }
                .id(),
                "GetAddressMac",
            ),
            (
                CheckAddressMac {
                    address_n: empty_u32.into(),
                    mac: [0u8; 32],
                    address: "".into(),
                    slip44: 0,
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
                    label: "".into(),
                    total: 0,
                }
                .id(),
                "Init",
            ),
            (Step { units: 0 }.id(), "Step"),
            (Label { label: "".into() }.id(), "Label"),
            (End.id(), "End"),
        ];
        // all IDs must be unique
        let mut seen = std::collections::HashSet::new();
        for (id, name) in variants {
            assert!(seen.insert(id), "duplicate id {} for variant {}", id, name);
        }
        // total count must match — add new variants here when extending the enum
        assert_eq!(variants.len(), 4, "new variant added but test not updated");
    }
}

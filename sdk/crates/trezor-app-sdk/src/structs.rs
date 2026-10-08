//! Low-level IPC message types for the Trezor UI, Crypto, and Progress interfaces.
//!
//! These types are serialized via [`rkyv`] and sent over IPC between the app
//! and the Core firmware task.
//!
//! Apps use `modui` and `crypto`, not these. Fields are `pub` because core
//! reads them straight off the archived (rkyv) form.

use rkyv::boxed::{ArchivedBox, BoxResolver};
use rkyv::rancor::Fallible;
use rkyv::ser::Writer;
use rkyv::{Archive, Deserialize, Place, Serialize, SerializeUnsized};
use ufmt::derive::uDebug;

/// A key-value pair with an optional monospace flag, used in UI detail views.
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize, Deserialize)]
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

/// A borrowed string slice wrapper, serialized as a relative pointer via rkyv.
/// Used instead of `&str` because rkyv cannot serialize `&str` directly.
#[derive(Copy, Clone, Default, PartialEq, Eq)]
pub struct StrSlice<'a> {
    inner: &'a str,
}

impl<'a> StrSlice<'a> {
    pub fn new(s: &'a str) -> Self {
        Self { inner: s }
    }

    pub fn as_str(&self) -> &'a str {
        self.inner
    }
}

// Manual uDebug: ufmt deliberately doesn't implement uDebug for `str` (it
// would need panic-prone char-escaping logic), so this just writes the raw
// contents, matching ufmt's own `uDisplay for str` behavior.
impl<'a> ufmt::uDebug for StrSlice<'a> {
    fn fmt<W: ?Sized>(&self, f: &mut ufmt::Formatter<'_, W>) -> Result<(), W::Error>
    where
        W: ufmt::uWrite,
    {
        f.write_str(self.inner)
    }
}

impl<'a> From<&'a str> for StrSlice<'a> {
    fn from(s: &'a str) -> Self {
        Self::new(s)
    }
}

// The archived form of StrSlice is rkyv's own ArchivedBox<str> — a
// #[repr(transparent)] RelPtr<str> wrapper that already carries a correct
// CheckBytes/Verify impl, so archived StrSlice values can be read via safe,
// validated rkyv::access instead of access_unchecked.
impl<'a> Archive for StrSlice<'a> {
    type Archived = ArchivedBox<str>;
    type Resolver = BoxResolver;

    fn resolve(&self, resolver: Self::Resolver, out: Place<Self::Archived>) {
        ArchivedBox::resolve_from_ref(self.inner, resolver, out)
    }
}

// We restrict our serializer types with Writer because we need its
// capabilities to serialize the inner string. For other types, we might
// need more or less restrictive bounds on the type of S.
impl<'a, S: Fallible + Writer + ?Sized> Serialize<S> for StrSlice<'a> {
    fn serialize(&self, serializer: &mut S) -> Result<Self::Resolver, S::Error> {
        ArchivedBox::serialize_from_ref(self.inner, serializer)
    }
}

/// A borrowed slice wrapper, serialized as a relative pointer via rkyv.
/// Used instead of `&[T]` for the same reason as [`StrSlice`].
pub struct Slice<'a, T: Archive> {
    inner: &'a [T],
}

// Manual Copy/Clone: `Slice` only ever copies the borrowed `&'a [T]` itself,
// never the elements, so it shouldn't require `T: Copy`/`T: Clone` the way a
// derive would.
impl<'a, T: Archive> Copy for Slice<'a, T> {}

impl<'a, T: Archive> Clone for Slice<'a, T> {
    fn clone(&self) -> Self {
        *self
    }
}

impl<'a, T: Archive + ufmt::uDebug> ufmt::uDebug for Slice<'a, T> {
    fn fmt<W: ?Sized>(&self, f: &mut ufmt::Formatter<'_, W>) -> Result<(), W::Error>
    where
        W: ufmt::uWrite,
    {
        self.inner.fmt(f)
    }
}

impl<'a, T: Archive + PartialEq> PartialEq for Slice<'a, T> {
    fn eq(&self, other: &Self) -> bool {
        self.inner == other.inner
    }
}

impl<'a, T: Archive + Eq> Eq for Slice<'a, T> {}

impl<'a, T: Archive> Slice<'a, T> {
    pub fn new(s: &'a [T]) -> Self {
        Self { inner: s }
    }

    pub fn as_slice(&self) -> &'a [T] {
        self.inner
    }

    pub fn len(&self) -> usize {
        self.inner.len()
    }

    pub fn is_empty(&self) -> bool {
        self.inner.is_empty()
    }

    pub fn get(&self, index: usize) -> Option<&T> {
        self.inner.get(index)
    }
}

impl<'a, T: Archive> From<&'a [T]> for Slice<'a, T> {
    fn from(s: &'a [T]) -> Self {
        Self::new(s)
    }
}

// The archived form of Slice<T> is rkyv's own ArchivedBox<[T::Archived]> —
// same rationale as StrSlice above: reuses rkyv's existing CheckBytes/Verify
// impl for unsized RelPtr pointees instead of hand-rolling one.
impl<'a, T: Archive> Archive for Slice<'a, T> {
    type Archived = ArchivedBox<[T::Archived]>;
    type Resolver = BoxResolver;

    fn resolve(&self, resolver: Self::Resolver, out: Place<Self::Archived>) {
        ArchivedBox::resolve_from_ref(self.inner, resolver, out)
    }
}

impl<'a, T: Archive, S: Fallible + Writer + ?Sized> Serialize<S> for Slice<'a, T>
where
    [T]: SerializeUnsized<S>,
{
    fn serialize(&self, serializer: &mut S) -> Result<Self::Resolver, S::Error> {
        ArchivedBox::serialize_from_ref(self.inner, serializer)
    }
}

/// A menu of selectable string items, sent as [`TrezorUiEnum::SelectMenu`].
///
/// Only the caller's items. A model whose screens give their way out up to
/// the menu button adds that way out itself.
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize)]
pub struct SelectMenu<'a> {
    pub items: Slice<'a, StrSlice<'a>>,
    pub br_name: Option<StrSlice<'a>>,
    pub br_code: i32,
}

impl<'a> SelectMenu<'a> {
    pub fn new(
        items: &'a [StrSlice<'a>],
        br_name: Option<&'a str>,
        br_code: i32,
    ) -> SelectMenu<'a> {
        SelectMenu {
            items: items.into(),
            br_name: br_name.map(|s| s.into()),
            br_code,
        }
    }
}

/// An action confirmation screen, sent as [`TrezorUiEnum::ConfirmAction`].
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize)]
pub struct ConfirmAction<'a> {
    pub title: StrSlice<'a>,
    pub action: StrSlice<'a>,
    pub description: Option<StrSlice<'a>>,
    pub subtitle: Option<StrSlice<'a>>,
    pub hold: bool,
    pub verb: Option<StrSlice<'a>>,
    pub br_name: Option<StrSlice<'a>>,
    pub br_code: i32,
    pub external_menu: bool,
}

impl<'a> ConfirmAction<'a> {
    pub fn new(
        title: &'a str,
        action: &'a str,
        description: Option<&'a str>,
        subtitle: Option<&'a str>,
        hold: bool,
        verb: Option<&'a str>,
        br_name: Option<&'a str>,
        br_code: i32,
        external_menu: bool,
    ) -> Self {
        Self {
            title: title.into(),
            action: action.into(),
            description: description.map(|s| s.into()),
            subtitle: subtitle.map(|s| s.into()),
            hold,
            verb: verb.map(|s| s.into()),
            br_name: br_name.map(|s| s.into()),
            br_code,
            external_menu,
        }
    }
}

/// A transaction summary confirmation screen, sent as [`TrezorUiEnum::ConfirmSummary`].
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize)]
pub struct ConfirmSummary<'a> {
    pub title: StrSlice<'a>,
    pub amount: Option<StrSlice<'a>>,
    pub amount_label: Option<StrSlice<'a>>,
    pub fee: StrSlice<'a>,
    pub fee_label: StrSlice<'a>,
    pub account_title: Option<StrSlice<'a>>,
    pub account_items: Option<Slice<'a, Property<'a>>>,
    pub extra_title: Option<StrSlice<'a>>,
    pub extra_items: Option<Slice<'a, Property<'a>>>,
    pub back_button: bool,
    pub external_menu: bool,
    pub br_name: Option<StrSlice<'a>>,
    pub br_code: i32,
}

impl<'a> ConfirmSummary<'a> {
    pub fn new(
        title: &'a str,
        amount: Option<&'a str>,
        amount_label: Option<&'a str>,
        fee: &'a str,
        fee_label: &'a str,
        account_title: Option<&'a str>,
        account_items: Option<&'a [Property<'a>]>,
        extra_title: Option<&'a str>,
        extra_items: Option<&'a [Property<'a>]>,
        back_button: bool,
        external_menu: bool,
        br_name: Option<&'a str>,
        br_code: i32,
    ) -> Self {
        Self {
            title: title.into(),
            amount: amount.map(|s| s.into()),
            amount_label: amount_label.map(|s| s.into()),
            fee: fee.into(),
            fee_label: fee_label.into(),
            account_title: account_title.map(|s| s.into()),
            account_items: account_items.map(|s| s.into()),
            extra_title: extra_title.map(|s| s.into()),
            extra_items: extra_items.map(|s| s.into()),
            back_button,
            external_menu,
            br_name: br_name.map(|s| s.into()),
            br_code,
        }
    }
}

/// A value confirmation screen, sent as [`TrezorUiEnum::ConfirmValue`].
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize)]
pub struct ConfirmValue<'a> {
    pub title: StrSlice<'a>,
    pub value: StrSlice<'a>,
    pub description: Option<StrSlice<'a>>,
    pub is_data: bool,
    pub subtitle: Option<StrSlice<'a>>,
    pub verb: Option<StrSlice<'a>>,
    pub info: bool,
    pub hold: bool,
    pub chunkify: bool,
    pub page_counter: bool,
    pub br_name: Option<StrSlice<'a>>,
    pub br_code: i32,
    pub external_menu: bool,
    pub footer: Option<(StrSlice<'a>, bool)>,
}

impl<'a> ConfirmValue<'a> {
    pub fn new(
        title: &'a str,
        content: &'a str,
        description: Option<&'a str>,
        br_name: Option<&'a str>,
        br_code: i32,
        is_data: bool,
        verb: Option<&'a str>,
        subtitle: Option<&'a str>,
        info: bool,
        hold: bool,
        chunkify: bool,
        page_counter: bool,
        external_menu: bool,
        footer: Option<(&'a str, bool)>,
    ) -> Self {
        Self {
            title: title.into(),
            value: content.into(),
            description: description.map(|s| s.into()),
            is_data,
            subtitle: subtitle.map(|s| s.into()),
            verb: verb.map(|s| s.into()),
            info,
            hold,
            chunkify,
            page_counter,
            br_name: br_name.map(|s| s.into()),
            br_code,
            external_menu,
            footer: footer.map(|(s, b)| (s.into(), b)),
        }
    }
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

/// A notice of some [`Severity`], sent by the app SDK.
///
/// Carries what the notice says and nothing about how it looks: no button
/// words, no timeout, no choice of screen. Core derives those from `severity`.
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize)]
pub struct ShowNotice<'a> {
    pub severity: Severity,
    pub title: StrSlice<'a>,
    pub content: StrSlice<'a>,
    /// The screen leads to the caller's menu of extras.
    pub external_menu: bool,
    /// The notice must offer a way to back out. How is the model's.
    /// WIP: ignored by every model.
    pub cancel: bool,
    pub br_name: Option<StrSlice<'a>>,
    pub br_code: i32,
}

impl<'a> ShowNotice<'a> {
    pub fn new(
        severity: Severity,
        title: &'a str,
        content: &'a str,
        external_menu: bool,
        cancel: bool,
        br_name: Option<&'a str>,
        br_code: i32,
    ) -> Self {
        Self {
            severity,
            title: title.into(),
            content: content.into(),
            external_menu,
            cancel,
            br_name: br_name.map(|s| s.into()),
            br_code,
        }
    }
}

/// A property-list confirmation screen, sent as
/// [`TrezorUiEnum::ConfirmProperties`].
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize)]
pub struct ConfirmProperties<'a> {
    pub title: StrSlice<'a>,
    pub props: Slice<'a, Property<'a>>,
    pub subtitle: Option<StrSlice<'a>>,
    pub verb: Option<StrSlice<'a>>,
    pub hold: bool,
    pub br_name: Option<StrSlice<'a>>,
    pub br_code: i32,
}

impl<'a> ConfirmProperties<'a> {
    pub fn new(
        title: &'a str,
        props: &'a [Property<'a>],
        subtitle: Option<&'a str>,
        verb: Option<&'a str>,
        hold: bool,
        br_name: Option<&'a str>,
        br_code: i32,
    ) -> Self {
        Self {
            title: title.into(),
            props: props.into(),
            subtitle: subtitle.map(|s| s.into()),
            verb: verb.map(|s| s.into()),
            hold,
            br_name: br_name.map(|s| s.into()),
            br_code,
        }
    }
}

/// A property-list display screen (no confirmation), sent as
/// [`TrezorUiEnum::ShowProperties`].
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize)]
pub struct ShowProperties<'a> {
    pub title: StrSlice<'a>,
    pub props: Slice<'a, Property<'a>>,
    pub subtitle: Option<StrSlice<'a>>,
    pub br_name: Option<StrSlice<'a>>,
    pub br_code: i32,
}

impl<'a> ShowProperties<'a> {
    pub fn new(
        title: &'a str,
        props: &'a [Property<'a>],
        subtitle: Option<&'a str>,
        br_name: Option<&'a str>,
        br_code: i32,
    ) -> Self {
        Self {
            title: title.into(),
            props: props.into(),
            subtitle: subtitle.map(|s| s.into()),
            br_name: br_name.map(|s| s.into()),
            br_code,
        }
    }
}

/// One UI request, as it crosses IPC: one variant per `modui` block, plus the
/// extras' menu and screen. Built by `core/embed/api` from the `traits::ui`
/// mirrors.
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize)]
pub enum TrezorUiEnum<'a> {
    SelectMenu(SelectMenu<'a>),
    ConfirmAction(ConfirmAction<'a>),
    ConfirmSummary(ConfirmSummary<'a>),
    ConfirmValue(ConfirmValue<'a>),
    ConfirmProperties(ConfirmProperties<'a>),
    ShowProperties(ShowProperties<'a>),
    ShowNotice(ShowNotice<'a>),
}

/// What the person did with one screen. Written by core, read by `modui`;
/// apps never see it.
///
/// Variants say what the person *did*, not which button did it. Wider than any
/// one request's contract (`Choice` only answers a list), so a reply a caller
/// cannot use is a protocol violation.
#[must_use]
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize, Deserialize)]
pub enum UiReply {
    /// Yes, having seen all of it.
    ///
    /// WIP: until `Forward` has a producer, every chunk of `confirm::data`
    /// answers this too.
    Confirmed,
    /// Refused, or left without answering. `modui` turns it into
    /// `Err(Error::Cancelled)`.
    Cancelled,
    /// The extras: the screen's menu button. Lateral, unlike `Forward`.
    WantsMore,
    /// Picked the list entry at this index, as sent.
    Choice(u16),
    /// Paged past the end of the content core holds; the sender has more.
    ///
    /// WIP: no producer yet.
    Forward,
    /// Paged back before the content core holds, or back a step.
    Backward,
    /// Accepted the rest without reading it.
    ///
    /// WIP: no producer yet.
    ConfirmedAll,
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
        description: Option<StrSlice<'a>>,
        title: Option<StrSlice<'a>>,
        indeterminate: bool,
        danger: bool,
    },
    Update {
        description: Option<StrSlice<'a>>,
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

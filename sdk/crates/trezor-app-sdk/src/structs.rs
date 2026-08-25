//! Low-level IPC message types for the Trezor UI, Crypto, and Progress interfaces.
//!
//! These types are serialized via [`rkyv`] and sent over IPC between the app
//! and the Core firmware task.
//!
//! **Prefer the higher-level `ui`/`crypto`/`progress` modules and each type's
//! `new()` constructor over building these directly.** Fields are `pub`
//! despite that, because Core reads them straight off the archived (rkyv)
//! form with no wrapper API of its own — that's the one legitimate reader
//! these fields need to stay public for.

use rkyv::boxed::{ArchivedBox, BoxResolver};
use rkyv::rancor::Fallible;
use rkyv::ser::Writer;
use rkyv::{Archive, Deserialize, Place, Serialize, SerializeUnsized};
use ufmt::derive::uDebug;

/// A key-value pair with an optional monospace flag, used in UI detail views.
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize, Deserialize)]
pub struct Property<'a> {
    pub key: StrSlice<'a>,
    pub value: StrSlice<'a>,
    pub mono: bool,
}

impl<'a> Property<'a> {
    pub fn new(key: &'a str, value: &'a str, mono: bool) -> Self {
        Self {
            key: key.into(),
            value: value.into(),
            mono,
        }
    }

    pub fn mono(key: &'a str, value: &'a str) -> Self {
        Self::new(key, value, true)
    }

    pub fn plain(key: &'a str, value: &'a str) -> Self {
        Self::new(key, value, false)
    }
}

/// A string with an optional monospace flag, used in UI list views.
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize, Deserialize)]
pub struct StrExt<'a> {
    pub key: StrSlice<'a>,
    pub mono: bool,
}

impl<'a> StrExt<'a> {
    pub fn new(key: &'a str, mono: bool) -> Self {
        Self {
            key: key.into(),
            mono,
        }
    }

    pub fn mono(key: &'a str) -> Self {
        Self::new(key, true)
    }

    pub fn plain(key: &'a str) -> Self {
        Self::new(key, false)
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

/// A menu of selectable string items, shown via [`crate::ui::select_menu`].
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize)]
pub struct SelectMenu<'a> {
    pub items: Slice<'a, StrSlice<'a>>,
    pub cancel: Option<StrSlice<'a>>,
    pub br_code: i32,
}

impl<'a> SelectMenu<'a> {
    pub fn new(items: &'a [StrSlice<'a>], cancel: Option<&'a str>, br_code: i32) -> SelectMenu<'a> {
        SelectMenu {
            items: items.into(),
            cancel: cancel.map(|s| s.into()),
            br_code,
        }
    }
}

/// A trade confirmation screen, shown via [`crate::ui::confirm_trade`].
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize)]
pub struct ConfirmTrade<'a> {
    pub title: StrSlice<'a>,
    pub subtitle: StrSlice<'a>,
    pub buy: StrSlice<'a>,
    pub sell: Option<StrSlice<'a>>,
    pub back_button: bool,
    pub br_name: Option<StrSlice<'a>>,
    pub br_code: i32,
}

impl<'a> ConfirmTrade<'a> {
    pub fn new(
        title: &'a str,
        subtitle: &'a str,
        buy: &'a str,
        sell: Option<&'a str>,
        back_button: bool,
        br_name: Option<&'a str>,
        br_code: i32,
    ) -> ConfirmTrade<'a> {
        ConfirmTrade {
            title: title.into(),
            subtitle: subtitle.into(),
            buy: buy.into(),
            sell: sell.map(|s| s.into()),
            back_button,
            br_name: br_name.map(|s| s.into()),
            br_code,
        }
    }
}

/// An action confirmation screen, shown via [`crate::ui::confirm_action`].
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize)]
pub struct ConfirmAction<'a> {
    pub title: StrSlice<'a>,
    pub action: StrSlice<'a>,
    pub description: Option<StrSlice<'a>>,
    pub subtitle: Option<StrSlice<'a>>,
    pub hold: bool,
    pub cancel: bool,
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
        cancel: bool,
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
            cancel,
            verb: verb.map(|s| s.into()),
            br_name: br_name.map(|s| s.into()),
            br_code,
            external_menu,
        }
    }
}

/// A transaction summary confirmation screen, shown via [`crate::ui::confirm_summary`].
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
            br_name: br_name.map(|s| s.into()),
            br_code,
        }
    }
}

/// A value confirmation screen, shown via [`crate::ui::confirm_value`].
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
    pub cancel: bool,
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
        cancel: bool,
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
            cancel,
            br_name: br_name.map(|s| s.into()),
            br_code,
            external_menu,
            footer: footer.map(|(s, b)| (s.into(), b)),
        }
    }
}

/// An intro screen shown before [`ConfirmValue`], via [`crate::ui::confirm_value_intro`].
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize)]
pub struct ConfirmValueIntro<'a> {
    pub title: StrSlice<'a>,
    pub value: StrSlice<'a>,
    pub subtitle: Option<StrSlice<'a>>,
    pub verb: Option<StrSlice<'a>>,
    pub verb_cancel: Option<StrSlice<'a>>,
    pub verb_view_all: Option<StrSlice<'a>>,
    pub hold: bool,
    pub chunkify: bool,
    pub br_name: Option<StrSlice<'a>>,
    pub br_code: i32,
}

impl<'a> ConfirmValueIntro<'a> {
    pub fn new(
        title: &'a str,
        value: &'a str,
        subtitle: Option<&'a str>,
        verb: Option<&'a str>,
        verb_cancel: Option<&'a str>,
        verb_view_all: Option<&'a str>,
        hold: bool,
        chunkify: bool,
        br_name: Option<&'a str>,
        br_code: i32,
    ) -> Self {
        Self {
            title: title.into(),
            value: value.into(),
            subtitle: subtitle.map(|s| s.into()),
            verb: verb.map(|s| s.into()),
            verb_cancel: verb_cancel.map(|s| s.into()),
            verb_view_all: verb_view_all.map(|s| s.into()),
            hold,
            chunkify,
            br_name: br_name.map(|s| s.into()),
            br_code,
        }
    }
}

/// A warning screen, shown via [`crate::ui::show_warning`].
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize)]
pub struct ShowWarning<'a> {
    pub title: StrSlice<'a>,
    pub content: StrSlice<'a>,
    pub verb: StrSlice<'a>,
    pub br_name: Option<StrSlice<'a>>,
    pub br_code: i32,
    pub allow_cancel: bool,
    pub danger: bool,
}

impl<'a> ShowWarning<'a> {
    pub fn new(
        title: &'a str,
        content: &'a str,
        verb: &'a str,
        br_name: Option<&'a str>,
        br_code: i32,
        allow_cancel: bool,
        danger: bool,
    ) -> Self {
        Self {
            title: title.into(),
            content: content.into(),
            verb: verb.into(),
            br_name: br_name.map(|s| s.into()),
            br_code,
            allow_cancel,
            danger,
        }
    }
}

/// A mismatch warning screen, shown via [`crate::ui::show_mismatch`].
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize)]
pub struct ShowMismatch<'a> {
    pub title: StrSlice<'a>,
    pub br_code: i32,
}

impl<'a> ShowMismatch<'a> {
    pub fn new(title: &'a str, br_code: i32) -> Self {
        Self {
            title: title.into(),
            br_code,
        }
    }
}

/// A danger warning screen, shown via [`crate::ui::show_danger`].
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize)]
pub struct ShowDanger<'a> {
    pub title: StrSlice<'a>,
    pub content: StrSlice<'a>,
    pub br_name: Option<StrSlice<'a>>,
    pub br_code: i32,
    pub verb_cancel: Option<StrSlice<'a>>,
    pub menu_title: Option<StrSlice<'a>>,
}

impl<'a> ShowDanger<'a> {
    pub fn new(
        title: &'a str,
        content: &'a str,
        br_name: Option<&'a str>,
        br_code: i32,
        verb_cancel: Option<&'a str>,
        menu_title: Option<&'a str>,
    ) -> Self {
        Self {
            title: title.into(),
            content: content.into(),
            br_name: br_name.map(|s| s.into()),
            br_code,
            verb_cancel: verb_cancel.map(|s| s.into()),
            menu_title: menu_title.map(|s| s.into()),
        }
    }
}

/// A success screen, shown via [`crate::ui::show_success`].
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize)]
pub struct ShowSuccess<'a> {
    pub title: StrSlice<'a>,
    pub content: StrSlice<'a>,
    pub button: StrSlice<'a>,
    pub duration_ms: Option<u32>,
    pub br_name: Option<StrSlice<'a>>,
    pub br_code: i32,
}

impl<'a> ShowSuccess<'a> {
    pub fn new(
        title: &'a str,
        content: &'a str,
        button: &'a str,
        duration_ms: Option<u32>,
        br_name: Option<&'a str>,
        br_code: i32,
    ) -> Self {
        Self {
            title: title.into(),
            content: content.into(),
            button: button.into(),
            duration_ms,
            br_name: br_name.map(|s| s.into()),
            br_code,
        }
    }
}

/// A number-entry screen, shown via [`crate::ui::request_number`].
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize)]
pub struct RequestNumber<'a> {
    pub title: StrSlice<'a>,
    pub content: StrSlice<'a>,
    pub initial: u32,
    pub min: u32,
    pub max: u32,
    pub br_code: i32,
}

impl<'a> RequestNumber<'a> {
    pub fn new(
        title: &'a str,
        content: &'a str,
        initial: u32,
        min: u32,
        max: u32,
        br_code: i32,
    ) -> Self {
        Self {
            title: title.into(),
            content: content.into(),
            initial,
            min,
            max,
            br_code,
        }
    }
}

/// A property-list confirmation screen, shown via [`crate::ui::confirm_properties`].
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

/// A property-list display screen (no confirmation), shown via [`crate::ui::show_properties`].
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

/// A public key display screen, shown via [`crate::ui::show_public_key`].
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize)]
pub struct ShowPublicKey<'a> {
    pub pubkey: StrSlice<'a>,
    pub title: StrSlice<'a>,
    pub account: Option<StrSlice<'a>>,
    pub path: Option<StrSlice<'a>>,
    pub warning: Option<StrSlice<'a>>,
    pub br_name: StrSlice<'a>,
    pub br_code: i32,
}

impl<'a> ShowPublicKey<'a> {
    pub fn new(
        pubkey: &'a str,
        title: &'a str,
        account: Option<&'a str>,
        path: Option<&'a str>,
        warning: Option<&'a str>,
        br_name: &'a str,
        br_code: i32,
    ) -> Self {
        Self {
            pubkey: pubkey.into(),
            title: title.into(),
            account: account.map(|s| s.into()),
            path: path.map(|s| s.into()),
            warning: warning.map(|s| s.into()),
            br_name: br_name.into(),
            br_code,
        }
    }
}

/// An info screen with a cancel option, shown via [`crate::ui::show_info_with_cancel`].
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize)]
pub struct ShowInfoWithCancel<'a> {
    pub title: StrSlice<'a>,
    pub items: Slice<'a, Property<'a>>,
    pub chunkify: bool,
    pub br_name: Option<StrSlice<'a>>,
    pub br_code: i32,
}

impl<'a> ShowInfoWithCancel<'a> {
    pub fn new(
        title: &'a str,
        items: &'a [Property<'a>],
        chunkify: bool,
        br_name: Option<&'a str>,
        br_code: i32,
    ) -> Self {
        Self {
            title: title.into(),
            items: items.into(),
            chunkify,
            br_name: br_name.map(|s| s.into()),
            br_code,
        }
    }
}
/// A confirmation screen with an extra info button, shown via [`crate::ui::confirm_with_info`].
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize)]
pub struct ConfirmWithInfo<'a> {
    pub title: StrSlice<'a>,
    pub subtitle: Option<StrSlice<'a>>,
    pub items: Slice<'a, StrExt<'a>>,
    pub verb: StrSlice<'a>,
    pub verb_info: Option<StrSlice<'a>>,
    pub br_name: Option<StrSlice<'a>>,
    pub br_code: i32,
}

impl ConfirmWithInfo<'_> {
    pub fn new<'a>(
        title: &'a str,
        subtitle: Option<&'a str>,
        items: &'a [StrExt<'a>],
        verb: &'a str,
        verb_info: Option<&'a str>,
        br_name: Option<&'a str>,
        br_code: i32,
    ) -> ConfirmWithInfo<'a> {
        ConfirmWithInfo {
            title: title.into(),
            subtitle: subtitle.map(|s| s.into()),
            items: items.into(),
            verb: verb.into(),
            verb_info: verb_info.map(|s| s.into()),
            br_name: br_name.map(|s| s.into()),
            br_code,
        }
    }
}

/// An address display screen, shown via [`crate::ui::show_address`].
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize)]
pub struct ShowAddress<'a> {
    pub address: StrSlice<'a>,
    pub address_qr: StrSlice<'a>,
    pub title: Option<StrSlice<'a>>,
    pub subtitle: Option<StrSlice<'a>>,
    pub account: Option<StrSlice<'a>>,
    pub path: Option<StrSlice<'a>>,
    pub xpubs: Slice<'a, Property<'a>>,
    pub chunkify: bool,
    pub br_code: i32,
    pub case_sensitive: bool,
}

impl ShowAddress<'_> {
    pub fn new<'a>(
        address: &'a str,
        address_qr: &'a str,
        title: Option<&'a str>,
        subtitle: Option<&'a str>,
        account: Option<&'a str>,
        path: Option<&'a str>,
        xpubs: &'a [Property<'a>],
        chunkify: bool,
        br_code: i32,
        case_sensitive: bool,
    ) -> ShowAddress<'a> {
        ShowAddress {
            address: address.into(),
            address_qr: address_qr.into(),
            title: title.map(|s| s.into()),
            subtitle: subtitle.map(|s| s.into()),
            account: account.map(|s| s.into()),
            path: path.map(|s| s.into()),
            xpubs: xpubs.into(),
            chunkify,
            br_code,
            case_sensitive,
        }
    }
}

/// All UI screens that can be requested from the app via IPC.
///
/// Each variant corresponds to one screen type in the Trezor UI. Constructed
/// by the higher-level `ui` module — do not construct variants directly.
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize)]
pub enum TrezorUiEnum<'a> {
    SelectMenu(SelectMenu<'a>),
    ConfirmTrade(ConfirmTrade<'a>),
    ConfirmAction(ConfirmAction<'a>),
    ConfirmSummary(ConfirmSummary<'a>),
    ConfirmValue(ConfirmValue<'a>),
    ConfirmValueIntro(ConfirmValueIntro<'a>),
    ShowWarning(ShowWarning<'a>),
    ShowMismatch(ShowMismatch<'a>),
    ShowDanger(ShowDanger<'a>),
    ShowSuccess(ShowSuccess<'a>),
    RequestNumber(RequestNumber<'a>),
    ConfirmProperties(ConfirmProperties<'a>),
    ShowProperties(ShowProperties<'a>),
    ShowPublicKey(ShowPublicKey<'a>),
    ShowInfoWithCancel(ShowInfoWithCancel<'a>),
    ConfirmWithInfo(ConfirmWithInfo<'a>),
    ShowAddress(ShowAddress<'a>),
}

/// Result returned by the Core task after a UI interaction.
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize, Deserialize)]
pub enum TrezorUiResult {
    Confirmed,
    Back,
    Cancelled,
    Info,
    Integer(u32),
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
    Xpub([u8; 111]),
    PublicKey(crate::alloc_types::Vec<u8>), // 32, 33 or 65 bytes depending on the curve
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
            Self::Xpub(xpub) => f.debug_tuple("Xpub")?.field(&&xpub[..])?.finish(),
            Self::PublicKey(key) => f.debug_tuple("PublicKey")?.field(&key.as_slice())?.finish(),
            Self::Signature(sig) => f.debug_tuple("Signature")?.field(&&sig[..])?.finish(),
            Self::AddressMac(mac) => f.debug_tuple("AddressMac")?.field(mac)?.finish(),
            Self::Boolean(b) => f.debug_tuple("Boolean")?.field(b)?.finish(),
        }
    }
}

/// Progress bar operations that can be requested from the app via IPC.
///
/// Constructed by the higher-level `progress` module — do not construct variants directly.
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

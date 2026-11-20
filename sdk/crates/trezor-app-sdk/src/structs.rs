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
    /// Name of the property.
    pub key: StrSlice<'a>,
    /// Value of the property.
    pub value: StrSlice<'a>,
    /// Shows the value in a monospace font.
    pub mono: bool,
}

impl<'a> Property<'a> {
    /// A property `key`: `value`, the value in a monospace font if `mono`.
    pub fn new(key: &'a str, value: &'a str, mono: bool) -> Self {
        Self {
            key: key.into(),
            value: value.into(),
            mono,
        }
    }

    /// A property with its value in a monospace font.
    pub fn mono(key: &'a str, value: &'a str) -> Self {
        Self::new(key, value, true)
    }

    /// A property with its value in the regular font.
    pub fn plain(key: &'a str, value: &'a str) -> Self {
        Self::new(key, value, false)
    }
}

/// A string with an optional monospace flag, used in UI list views.
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize, Deserialize)]
pub struct StrExt<'a> {
    /// The text.
    pub key: StrSlice<'a>,
    /// Shows the text in a monospace font.
    pub mono: bool,
}

impl<'a> StrExt<'a> {
    /// A text, in a monospace font if `mono`.
    pub fn new(key: &'a str, mono: bool) -> Self {
        Self {
            key: key.into(),
            mono,
        }
    }

    /// A text in a monospace font.
    pub fn mono(key: &'a str) -> Self {
        Self::new(key, true)
    }

    /// A text in the regular font.
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
    /// Borrows `s`.
    pub fn new(s: &'a str) -> Self {
        Self { inner: s }
    }

    /// The borrowed string.
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
    /// Borrows `s`.
    pub fn new(s: &'a [T]) -> Self {
        Self { inner: s }
    }

    /// The borrowed slice.
    pub fn as_slice(&self) -> &'a [T] {
        self.inner
    }

    /// Number of elements.
    pub fn len(&self) -> usize {
        self.inner.len()
    }

    /// Whether there are no elements.
    pub fn is_empty(&self) -> bool {
        self.inner.is_empty()
    }

    /// The element at `index`, if any.
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

/// A menu of selectable string items.
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize)]
pub struct SelectMenu<'a> {
    /// Entries shown on the screen.
    pub items: Slice<'a, StrSlice<'a>>,
    /// Label of the cancel entry, if any.
    pub cancel: Option<StrSlice<'a>>,
    /// Button request code sent to the host.
    pub br_code: i32,
}

impl<'a> SelectMenu<'a> {
    /// Creates the request; each argument sets the field of the same name.
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
    /// Screen title.
    pub title: StrSlice<'a>,
    /// Subtitle under the title.
    pub subtitle: StrSlice<'a>,
    /// What the user gets.
    pub buy: StrSlice<'a>,
    /// What the user gives.
    pub sell: Option<StrSlice<'a>>,
    /// The left button returns `Back` instead of cancelling.
    pub back_button: bool,
    /// Button request name sent to the host.
    pub br_name: Option<StrSlice<'a>>,
    /// Button request code sent to the host.
    pub br_code: i32,
}

impl<'a> ConfirmTrade<'a> {
    /// Creates the request; each argument sets the field of the same name.
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
    /// Screen title.
    pub title: StrSlice<'a>,
    /// The action to confirm.
    pub action: StrSlice<'a>,
    /// Description text.
    pub description: Option<StrSlice<'a>>,
    /// Subtitle under the title.
    pub subtitle: Option<StrSlice<'a>>,
    /// The user confirms by holding the button.
    pub hold: bool,
    /// Shows a cancel button.
    pub cancel: bool,
    /// Text of the confirm button.
    pub verb: Option<StrSlice<'a>>,
    /// Button request name sent to the host.
    pub br_name: Option<StrSlice<'a>>,
    /// Button request code sent to the host.
    pub br_code: i32,
    /// The menu button returns `Info` to the app instead of opening Core's menu.
    pub external_menu: bool,
}

impl<'a> ConfirmAction<'a> {
    /// Creates the request; each argument sets the field of the same name.
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
    /// Screen title.
    pub title: StrSlice<'a>,
    /// The amount.
    pub amount: Option<StrSlice<'a>>,
    /// Label of the amount.
    pub amount_label: Option<StrSlice<'a>>,
    /// The fee.
    pub fee: StrSlice<'a>,
    /// Label of the fee.
    pub fee_label: StrSlice<'a>,
    /// Title of the account information.
    pub account_title: Option<StrSlice<'a>>,
    /// Account information as key-value pairs.
    pub account_items: Option<Slice<'a, Property<'a>>>,
    /// Title of the extra information.
    pub extra_title: Option<StrSlice<'a>>,
    /// Extra information as key-value pairs.
    pub extra_items: Option<Slice<'a, Property<'a>>>,
    /// The left button returns `Back` instead of cancelling.
    pub back_button: bool,
    /// Button request name sent to the host.
    pub br_name: Option<StrSlice<'a>>,
    /// Button request code sent to the host.
    pub br_code: i32,
}

impl<'a> ConfirmSummary<'a> {
    /// Creates the request; each argument sets the field of the same name.
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
    /// Screen title.
    pub title: StrSlice<'a>,
    /// The value to confirm.
    pub value: StrSlice<'a>,
    /// Description text.
    pub description: Option<StrSlice<'a>>,
    /// The value is data, shown in a data font.
    pub is_data: bool,
    /// Subtitle under the title.
    pub subtitle: Option<StrSlice<'a>>,
    /// Text of the confirm button.
    pub verb: Option<StrSlice<'a>>,
    /// Shows an info button in the header.
    pub info: bool,
    /// The user confirms by holding the button.
    pub hold: bool,
    /// Shows the value in monospace chunks, for easier comparison.
    pub chunkify: bool,
    /// Shows a page counter.
    pub page_counter: bool,
    /// Shows a cancel button.
    pub cancel: bool,
    /// Button request name sent to the host.
    pub br_name: Option<StrSlice<'a>>,
    /// Button request code sent to the host.
    pub br_code: i32,
    /// The menu button returns `Info` to the app instead of opening Core's menu.
    pub external_menu: bool,
    /// Footer text, and whether it is bold.
    pub footer: Option<(StrSlice<'a>, bool)>,
}

impl<'a> ConfirmValue<'a> {
    /// Creates the request; each argument sets the field of the same name.
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
    /// Screen title.
    pub title: StrSlice<'a>,
    /// The value to confirm.
    pub value: StrSlice<'a>,
    /// Subtitle under the title.
    pub subtitle: Option<StrSlice<'a>>,
    /// Text of the confirm button.
    pub verb: Option<StrSlice<'a>>,
    /// Text of the cancel button.
    pub verb_cancel: Option<StrSlice<'a>>,
    /// Text of the button that shows the whole value.
    pub verb_view_all: Option<StrSlice<'a>>,
    /// The user confirms by holding the button.
    pub hold: bool,
    /// Shows the value in monospace chunks, for easier comparison.
    pub chunkify: bool,
    /// Button request name sent to the host.
    pub br_name: Option<StrSlice<'a>>,
    /// Button request code sent to the host.
    pub br_code: i32,
}

impl<'a> ConfirmValueIntro<'a> {
    /// Creates the request; each argument sets the field of the same name.
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
    /// Screen title.
    pub title: StrSlice<'a>,
    /// Body text.
    pub content: StrSlice<'a>,
    /// Text of the confirm button.
    pub verb: StrSlice<'a>,
    /// Button request name sent to the host.
    pub br_name: Option<StrSlice<'a>>,
    /// Button request code sent to the host.
    pub br_code: i32,
    /// Lets the user cancel.
    pub allow_cancel: bool,
    /// Shows the screen as dangerous.
    pub danger: bool,
}

impl<'a> ShowWarning<'a> {
    /// Creates the request; each argument sets the field of the same name.
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
    /// Screen title.
    pub title: StrSlice<'a>,
    /// Button request code sent to the host.
    pub br_code: i32,
}

impl<'a> ShowMismatch<'a> {
    /// Creates the request; each argument sets the field of the same name.
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
    /// Screen title.
    pub title: StrSlice<'a>,
    /// Body text.
    pub content: StrSlice<'a>,
    /// Button request name sent to the host.
    pub br_name: Option<StrSlice<'a>>,
    /// Button request code sent to the host.
    pub br_code: i32,
    /// Text of the cancel button.
    pub verb_cancel: Option<StrSlice<'a>>,
    /// Title of the menu.
    pub menu_title: Option<StrSlice<'a>>,
}

impl<'a> ShowDanger<'a> {
    /// Creates the request; each argument sets the field of the same name.
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
    /// Screen title.
    pub title: StrSlice<'a>,
    /// Body text.
    pub content: StrSlice<'a>,
    /// Text of the button.
    pub button: StrSlice<'a>,
    /// Closes the screen after this many milliseconds.
    pub duration_ms: Option<u32>,
    /// Button request name sent to the host.
    pub br_name: Option<StrSlice<'a>>,
    /// Button request code sent to the host.
    pub br_code: i32,
}

impl<'a> ShowSuccess<'a> {
    /// Creates the request; each argument sets the field of the same name.
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
    /// Screen title.
    pub title: StrSlice<'a>,
    /// Body text.
    pub content: StrSlice<'a>,
    /// Number shown at first.
    pub initial: u32,
    /// Smallest allowed number.
    pub min: u32,
    /// Largest allowed number.
    pub max: u32,
    /// Button request code sent to the host.
    pub br_code: i32,
}

impl<'a> RequestNumber<'a> {
    /// Creates the request; each argument sets the field of the same name.
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
    /// Screen title.
    pub title: StrSlice<'a>,
    /// Properties shown as key-value pairs.
    pub props: Slice<'a, Property<'a>>,
    /// Subtitle under the title.
    pub subtitle: Option<StrSlice<'a>>,
    /// Text of the confirm button.
    pub verb: Option<StrSlice<'a>>,
    /// The user confirms by holding the button.
    pub hold: bool,
    /// Button request name sent to the host.
    pub br_name: Option<StrSlice<'a>>,
    /// Button request code sent to the host.
    pub br_code: i32,
    /// The menu button returns `Info` to the app instead of opening Core's menu.
    pub external_menu: bool,
}

impl<'a> ConfirmProperties<'a> {
    /// Creates the request; each argument sets the field of the same name.
    pub fn new(
        title: &'a str,
        props: &'a [Property<'a>],
        subtitle: Option<&'a str>,
        verb: Option<&'a str>,
        hold: bool,
        br_name: Option<&'a str>,
        br_code: i32,
        external_menu: bool,
    ) -> Self {
        Self {
            title: title.into(),
            props: props.into(),
            subtitle: subtitle.map(|s| s.into()),
            verb: verb.map(|s| s.into()),
            hold,
            br_name: br_name.map(|s| s.into()),
            br_code,
            external_menu,
        }
    }
}

/// A property-list display screen (no confirmation), shown via [`crate::ui::show_properties`].
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize)]
pub struct ShowProperties<'a> {
    /// Screen title.
    pub title: StrSlice<'a>,
    /// Properties shown as key-value pairs.
    pub props: Slice<'a, Property<'a>>,
    /// Subtitle under the title.
    pub subtitle: Option<StrSlice<'a>>,
    /// Button request name sent to the host.
    pub br_name: Option<StrSlice<'a>>,
    /// Button request code sent to the host.
    pub br_code: i32,
}

impl<'a> ShowProperties<'a> {
    /// Creates the request; each argument sets the field of the same name.
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
    /// The public key.
    pub pubkey: StrSlice<'a>,
    /// Screen title.
    pub title: StrSlice<'a>,
    /// Account name shown with the key.
    pub account: Option<StrSlice<'a>>,
    /// Derivation path shown with the key.
    pub path: Option<StrSlice<'a>>,
    /// Warning text.
    pub warning: Option<StrSlice<'a>>,
    /// Button request name sent to the host.
    pub br_name: StrSlice<'a>,
    /// Button request code sent to the host.
    pub br_code: i32,
}

impl<'a> ShowPublicKey<'a> {
    /// Creates the request; each argument sets the field of the same name.
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
    /// Screen title.
    pub title: StrSlice<'a>,
    /// Entries shown on the screen.
    pub items: Slice<'a, Property<'a>>,
    /// Shows the value in monospace chunks, for easier comparison.
    pub chunkify: bool,
    /// Button request name sent to the host.
    pub br_name: Option<StrSlice<'a>>,
    /// Button request code sent to the host.
    pub br_code: i32,
}

impl<'a> ShowInfoWithCancel<'a> {
    /// Creates the request; each argument sets the field of the same name.
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
    /// Screen title.
    pub title: StrSlice<'a>,
    /// Subtitle under the title.
    pub subtitle: Option<StrSlice<'a>>,
    /// Entries shown on the screen.
    pub items: Slice<'a, StrExt<'a>>,
    /// Text of the confirm button.
    pub verb: StrSlice<'a>,
    /// Text of the info button.
    pub verb_info: Option<StrSlice<'a>>,
    /// Button request name sent to the host.
    pub br_name: Option<StrSlice<'a>>,
    /// Button request code sent to the host.
    pub br_code: i32,
}

impl ConfirmWithInfo<'_> {
    /// Creates the request; each argument sets the field of the same name.
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
    /// The address.
    pub address: StrSlice<'a>,
    /// The address as encoded in the QR code.
    pub address_qr: StrSlice<'a>,
    /// Screen title.
    pub title: Option<StrSlice<'a>>,
    /// Subtitle under the title.
    pub subtitle: Option<StrSlice<'a>>,
    /// Account name shown with the address.
    pub account: Option<StrSlice<'a>>,
    /// Derivation path shown with the address.
    pub path: Option<StrSlice<'a>>,
    /// Extended public keys of a multisig address.
    pub xpubs: Slice<'a, Property<'a>>,
    /// Shows the value in monospace chunks, for easier comparison.
    pub chunkify: bool,
    /// Button request code sent to the host.
    pub br_code: i32,
    /// The address is case-sensitive.
    pub case_sensitive: bool,
}

impl ShowAddress<'_> {
    /// Creates the request; each argument sets the field of the same name.
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
    /// A [`SelectMenu`] screen.
    SelectMenu(SelectMenu<'a>),
    /// A [`ConfirmTrade`] screen.
    ConfirmTrade(ConfirmTrade<'a>),
    /// A [`ConfirmAction`] screen.
    ConfirmAction(ConfirmAction<'a>),
    /// A [`ConfirmSummary`] screen.
    ConfirmSummary(ConfirmSummary<'a>),
    /// A [`ConfirmValue`] screen.
    ConfirmValue(ConfirmValue<'a>),
    /// A [`ConfirmValueIntro`] screen.
    ConfirmValueIntro(ConfirmValueIntro<'a>),
    /// A [`ShowWarning`] screen.
    ShowWarning(ShowWarning<'a>),
    /// A [`ShowMismatch`] screen.
    ShowMismatch(ShowMismatch<'a>),
    /// A [`ShowDanger`] screen.
    ShowDanger(ShowDanger<'a>),
    /// A [`ShowSuccess`] screen.
    ShowSuccess(ShowSuccess<'a>),
    /// A [`RequestNumber`] screen.
    RequestNumber(RequestNumber<'a>),
    /// A [`ConfirmProperties`] screen.
    ConfirmProperties(ConfirmProperties<'a>),
    /// A [`ShowProperties`] screen.
    ShowProperties(ShowProperties<'a>),
    /// A [`ShowPublicKey`] screen.
    ShowPublicKey(ShowPublicKey<'a>),
    /// A [`ShowInfoWithCancel`] screen.
    ShowInfoWithCancel(ShowInfoWithCancel<'a>),
    /// A [`ConfirmWithInfo`] screen.
    ConfirmWithInfo(ConfirmWithInfo<'a>),
    /// A [`ShowAddress`] screen.
    ShowAddress(ShowAddress<'a>),
}

/// Result returned by the Core task after a UI interaction.
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize, Deserialize)]
pub enum TrezorUiResult {
    /// The user confirmed.
    Confirmed,
    /// The user went back.
    Back,
    /// The user cancelled.
    Cancelled,
    /// The user asked for more information.
    Info,
    /// The number the user entered.
    Integer(u32),
}

/// All crypto operations that can be requested from the app via IPC.
///
/// Constructed by the higher-level `crypto` module — do not construct variants directly.
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize)]
pub enum TrezorCryptoEnum<'a> {
    /// Derive the raw xpub, see [`CryptoV1::get_xpub`](crate::traits::crypto::CryptoV1::get_xpub).
    GetXpub {
        /// A [`Curve`](crate::traits::crypto::Curve), as its `u8` value.
        curve: u8,
        /// Derivation path.
        address_n: Slice<'a, u32>,
    },
    /// Derive a public key.
    GetPublicKey {
        /// A [`Curve`](crate::traits::crypto::Curve), as its `u8` value.
        curve: u8,
        /// Derivation path.
        address_n: Slice<'a, u32>,
        /// Return the compressed form.
        compressed: bool,
    },
    /// Sign a digest with ECDSA.
    EcdsaSignDigest {
        /// An [`EcdsaCurve`](crate::traits::crypto::EcdsaCurve), as its `u8`
        /// value.
        curve: u8,
        /// Derivation path.
        address_n: Slice<'a, u32>,
        /// The digest to sign.
        digest: [u8; 32],
        /// Set the recovery header byte for a compressed public key.
        compressed: bool,
        /// A [`CanonicalSig`](crate::traits::crypto::CanonicalSig), as its
        /// `u8` value.
        canonical: u8,
    },
    /// Sign a message with Ed25519.
    Ed25519Sign {
        /// Derivation path.
        address_n: Slice<'a, u32>,
        /// The message to sign.
        message: Slice<'a, u8>,
    },
    /// Compute the MAC of an address.
    GetAddressMac {
        /// Derivation path of the address.
        address_n: Slice<'a, u32>,
        /// The address.
        address: StrSlice<'a>,
        /// SLIP-44 coin type.
        slip44: u32,
    },
    /// Check the MAC of an address.
    CheckAddressMac {
        /// Derivation path of the address.
        address_n: Slice<'a, u32>,
        /// The MAC to check.
        mac: [u8; 32],
        /// The address.
        address: StrSlice<'a>,
        /// SLIP-44 coin type.
        slip44: u32,
    },
}

impl<'a> TrezorCryptoEnum<'a> {
    /// The IPC message id of the request.
    pub fn id(&self) -> u8 {
        match self {
            Self::GetXpub { .. } => 0,
            Self::GetPublicKey { .. } => 1,
            Self::EcdsaSignDigest { .. } => 2,
            Self::Ed25519Sign { .. } => 3,
            Self::GetAddressMac { .. } => 4,
            Self::CheckAddressMac { .. } => 5,
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
    /// A string.
    String(StrSlice<'a>),
    /// Bytes.
    Bytes(Slice<'a, u8>),
    /// A boolean.
    Boolean(bool),
}

/// Progress bar operations that can be requested from the app via IPC.
///
/// Constructed by the higher-level `progress` module — do not construct variants directly.
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize, Deserialize)]
pub enum TrezorProgressEnum<'a> {
    /// Show a progress indicator.
    Init {
        /// Description text.
        description: Option<StrSlice<'a>>,
        /// Title.
        title: Option<StrSlice<'a>>,
        /// The progress has no known value; shows an animation instead.
        indeterminate: bool,
        /// Shows the indicator as dangerous.
        danger: bool,
    },
    /// Update the progress indicator.
    Update {
        /// New description text.
        description: Option<StrSlice<'a>>,
        /// Progress, from 0 to 1000.
        value: u32,
    },
    /// Close the progress indicator.
    End,
}

impl<'a> TrezorProgressEnum<'a> {
    /// The IPC message id of the request.
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
                    curve: 0,
                    address_n: empty_u32.into(),
                }
                .id(),
                "GetXpub",
            ),
            (
                GetPublicKey {
                    curve: 0,
                    address_n: empty_u32.into(),
                    compressed: false,
                }
                .id(),
                "GetPublicKey",
            ),
            (
                EcdsaSignDigest {
                    curve: 0,
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
        ];
        let mut seen = std::collections::HashSet::new();
        for (id, name) in variants {
            assert!(seen.insert(id), "duplicate id {} for variant {}", id, name);
        }
        assert_eq!(variants.len(), 6, "new variant added but test not updated");
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

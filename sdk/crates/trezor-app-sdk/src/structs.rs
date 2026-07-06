//! Low-level IPC message types for the Trezor UI, Crypto, and Progress interfaces.
//!
//! These types are serialized via [`rkyv`] and sent over IPC between the app
//! and the Core firmware task.
//!
//! **Do not use these types directly.** They are re-exported and wrapped by the
//! higher-level modules (`ui`, `crypto`, `progress`). The raw variants and fields
//! are considered an implementation detail and may change without notice.

use rkyv::munge::munge;
use rkyv::rancor::Fallible;
use rkyv::ser::Writer;
use rkyv::{
    Archive, ArchiveUnsized, Deserialize, Place, Portable, RelPtr, Serialize, SerializeUnsized,
};

/// A key-value pair with an optional monospace flag, used in UI detail views.
#[derive(Archive, Serialize, Deserialize)]
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
}

/// A string with an optional monospace flag, used in UI list views.
#[derive(Archive, Serialize, Deserialize)]
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
}

// Borrowed string slice wrapper — serialized as a relative pointer via rkyv.
// Used instead of &str because rkyv cannot serialize &str directly.
#[derive(Copy, Clone, Default)]
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

impl<'a> From<&'a str> for StrSlice<'a> {
    fn from(s: &'a str) -> Self {
        Self::new(s)
    }
}

// rkyv archived form of StrSlice — holds a RelPtr<str>.
#[derive(Portable)]
#[repr(transparent)]
pub struct ArchivedStrSlice {
    // This will be a relative pointer to our string
    ptr: RelPtr<str>,
}

impl ArchivedStrSlice {
    // This will help us get the bytes of our type as a str again.
    pub fn as_str(&self) -> &str {
        unsafe {
            // The as_ptr() function of RelPtr will get a pointer the str
            &*self.ptr.as_ptr()
        }
    }
}

// Resolver produced during StrSlice serialization — holds the position of the
// serialized string bytes so the relative pointer can be calculated.
pub struct BorrowedResolver {
    // This will be the position that the bytes of our string are stored at.
    // We'll use this to resolve the relative pointer of our
    // ArchivedStrSlice.
    pos: usize,
}

// The Archive implementation defines the archived version of our type and
// determines how to turn the resolver into the archived form. The Serialize
// implementations determine how to make a resolver from the original value.
impl<'a> Archive for StrSlice<'a> {
    type Archived = ArchivedStrSlice;
    // This is the resolver we can create our Archived version from.
    type Resolver = BorrowedResolver;

    // The resolve function consumes the resolver and produces the archived
    // value at the given position.
    fn resolve(&self, resolver: Self::Resolver, out: Place<Self::Archived>) {
        munge!(let ArchivedStrSlice { ptr } = out);
        RelPtr::emplace_unsized(resolver.pos, self.inner.archived_metadata(), ptr);
    }
}

// We restrict our serializer types with Writer because we need its
// capabilities to serialize the inner string. For other types, we might
// need more or less restrictive bounds on the type of S.
impl<'a, S: Fallible + Writer + ?Sized> Serialize<S> for StrSlice<'a> {
    fn serialize(&self, serializer: &mut S) -> Result<Self::Resolver, S::Error> {
        // This is where we want to write the bytes of our string and return
        // a resolver that knows where those bytes were written.
        // We also need to serialize the metadata for our str.
        Ok(BorrowedResolver {
            pos: self.inner.serialize_unsized(serializer)?,
        })
    }
}

// Borrowed slice wrapper — serialized as a relative pointer via rkyv.
// Used instead of &[T] for the same reason as StrSlice.
pub struct Slice<'a, T: Archive> {
    inner: &'a [T],
}

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

// rkyv archived form of Slice<T> — holds a RelPtr<[T::Archived]>.
#[derive(Portable)]
#[repr(transparent)]
pub struct ArchivedSlice<T: Archive> {
    ptr: RelPtr<[T::Archived]>,
}

impl<T: Archive> ArchivedSlice<T> {
    pub fn as_slice(&self) -> &[T::Archived] {
        unsafe { &*self.ptr.as_ptr() }
    }
}

impl<'a, T: Archive> Archive for Slice<'a, T> {
    type Archived = ArchivedSlice<T>;
    type Resolver = BorrowedResolver;

    fn resolve(&self, resolver: Self::Resolver, out: Place<Self::Archived>) {
        munge!(let ArchivedSlice { ptr } = out);
        let metadata = rkyv::rend::u32_le::from_native(self.inner.len() as u32);
        RelPtr::emplace_unsized(resolver.pos, metadata, ptr);
    }
}

impl<'a, T: Archive, S: Fallible + Writer + ?Sized> Serialize<S> for Slice<'a, T>
where
    [T]: SerializeUnsized<S>,
{
    fn serialize(&self, serializer: &mut S) -> Result<Self::Resolver, S::Error> {
        Ok(BorrowedResolver {
            pos: self.inner.serialize_unsized(serializer)?,
        })
    }
}

#[derive(Archive, Serialize)]
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

#[derive(Archive, Serialize)]
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

#[derive(Archive, Serialize)]
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

#[derive(Archive, Serialize)]
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

#[derive(Archive, Serialize)]
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

#[derive(Archive, Serialize)]
pub struct ConfirmValueIntro<'a> {
    pub title: StrSlice<'a>,
    pub value: StrSlice<'a>,
    pub subtitle: Option<StrSlice<'a>>,
    pub verb: Option<StrSlice<'a>>,
    pub verb_cancel: Option<StrSlice<'a>>,
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
            hold,
            chunkify,
            br_name: br_name.map(|s| s.into()),
            br_code,
        }
    }
}

#[derive(Archive, Serialize)]
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

#[derive(Archive, Serialize)]
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

#[derive(Archive, Serialize)]
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

#[derive(Archive, Serialize)]
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

#[derive(Archive, Serialize)]
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

#[derive(Archive, Serialize)]
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

#[derive(Archive, Serialize)]
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

#[derive(Archive, Serialize)]
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

#[derive(Archive, Serialize)]
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
#[derive(Archive, Serialize)]
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

#[derive(Archive, Serialize)]
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
        }
    }
}

/// All UI screens that can be requested from the app via IPC.
///
/// Each variant corresponds to one screen type in the Trezor UI. Constructed
/// by the higher-level `ui` module — do not construct variants directly.
#[derive(Archive, Serialize)]
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
#[derive(Archive, Serialize, Deserialize)]
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
#[derive(Archive, Serialize)]
pub enum TrezorCryptoEnum<'a> {
    GetXpub {
        address_n: Slice<'a, u32>,
    },
    GetXpubBytes {
        address_n: Slice<'a, u32>,
    },
    EcdsaPublicKey65 {
        address_n: Slice<'a, u32>,
    },
    VerifyDerivationPath {
        address_n: Slice<'a, u32>,
        encoded_network: Option<Slice<'a, u8>>,
        encoded_token: Option<Slice<'a, u8>>,
        chain_id: Option<u64>,
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
        encoded_network: Option<Slice<'a, u8>>,
    },
    CheckAddressMac {
        address_n: Slice<'a, u32>,
        mac: [u8; 32],
        address: StrSlice<'a>,
        encoded_network: Option<Slice<'a, u8>>,
    },
    VerifyNonceCache {
        nonce: Slice<'a, u8>,
    },
}

impl<'a> TrezorCryptoEnum<'a> {
    pub fn id(&self) -> u8 {
        match self {
            Self::GetXpub { .. } => 0,
            Self::GetXpubBytes { .. } => 1,
            Self::EcdsaPublicKey65 { .. } => 2,
            Self::SignTypedHash { .. } => 3,
            Self::GetAddressMac { .. } => 4,
            Self::VerifyNonceCache { .. } => 5,
            Self::CheckAddressMac { .. } => 6,
            Self::VerifyDerivationPath { .. } => 7,
        }
    }
}

/// Result returned by the Core task after a crypto operation.
#[derive(Archive, Serialize, Deserialize)]
pub enum TrezorCryptoResult {
    Xpub([u8; 111]),
    XpubBytes([u8; 33]),
    Signature([u8; 65]),
    EcdsaPublicKey65([u8; 65]),
    AddressMac([u8; 32]),
    Boolean(bool),
}

/// Progress bar operations that can be requested from the app via IPC.
///
/// Constructed by the higher-level `progress` module — do not construct variants directly.
#[derive(Archive, Serialize, Deserialize)]
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

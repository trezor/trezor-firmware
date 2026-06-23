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

/// Fixed-capacity UTF-8 string for `no_std`, stored as `[u8; N]` + length.
///
/// Used as a serializable alternative to `heapless::String` in IPC messages.
/// Prefer the higher-level string APIs over constructing this directly.
#[derive(Archive, Serialize, Deserialize, Copy, Clone)]
pub struct String<const N: usize> {
    pub data: [u8; N],
    pub len: usize,
}

impl<const N: usize> String<N> {
    fn as_slice(&self) -> &[u8] {
        &self.data[..self.len]
    }

    /// Returns the string contents, panicking if the stored bytes are not valid UTF-8.
    ///
    /// # Safety
    /// Valid UTF-8 is enforced at construction time via [`from_slice`](Self::from_slice).
    /// This function is safe to call as long as `String` was not constructed manually.
    pub fn as_str(&self) -> &str {
        crate::unwrap!(
            core::str::from_utf8(self.as_slice()),
            "String contains invalid UTF-8"
        )
    }

    /// Constructs a `String<N>` from a byte slice.
    ///
    /// Returns `Err(())` if `slice.len() > N`.
    pub fn from_slice(slice: &[u8]) -> core::result::Result<Self, ()> {
        if slice.len() > N {
            // TODO: better error handling
            return Err(());
        }
        let mut data = [0u8; N];
        data[..slice.len()].copy_from_slice(slice);
        Ok(Self {
            data,
            len: slice.len(),
        })
    }
}

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

/// All UI screens that can be requested from the app via IPC.
///
/// Each variant corresponds to one screen type in the Trezor UI. Constructed
/// by the higher-level `ui` module — do not construct variants directly.
#[derive(Archive, Serialize)]
pub enum TrezorUiEnum<'a> {
    SelectMenu {
        items: Slice<'a, StrSlice<'a>>,
        cancel: Option<StrSlice<'a>>,
        br_code: i32,
    },
    ConfirmTrade {
        title: StrSlice<'a>,
        subtitle: StrSlice<'a>,
        buy: StrSlice<'a>,
        sell: Option<StrSlice<'a>>,
        back_button: bool,
        br_name: Option<StrSlice<'a>>,
        br_code: i32,
    },
    ConfirmAction {
        title: StrSlice<'a>,
        action: StrSlice<'a>,
        description: Option<StrSlice<'a>>,
        subtitle: Option<StrSlice<'a>>,
        hold: bool,
        cancel: bool,
        verb: Option<StrSlice<'a>>,
        br_name: Option<StrSlice<'a>>,
        br_code: i32,
        external_menu: bool,
    },
    ConfirmSummary {
        title: StrSlice<'a>,
        amount: Option<StrSlice<'a>>,
        amount_label: Option<StrSlice<'a>>,
        fee: StrSlice<'a>,
        fee_label: StrSlice<'a>,
        account_title: Option<StrSlice<'a>>,
        account_items: Option<Slice<'a, Property<'a>>>,
        extra_title: Option<StrSlice<'a>>,
        extra_items: Option<Slice<'a, Property<'a>>>,
        back_button: bool,
        br_name: Option<StrSlice<'a>>,
        br_code: i32,
    },
    ConfirmValue {
        title: StrSlice<'a>,
        value: StrSlice<'a>,
        description: Option<StrSlice<'a>>,
        is_data: bool,
        subtitle: Option<StrSlice<'a>>,
        verb: Option<StrSlice<'a>>,
        info: bool,
        hold: bool,
        chunkify: bool,
        page_counter: bool,
        cancel: bool,
        br_name: Option<StrSlice<'a>>,
        br_code: i32,
        external_menu: bool,
        footer: Option<(StrSlice<'a>, bool)>,
    },
    ConfirmValueIntro {
        title: StrSlice<'a>,
        value: StrSlice<'a>,
        subtitle: Option<StrSlice<'a>>,
        verb: Option<StrSlice<'a>>,
        verb_cancel: Option<StrSlice<'a>>,
        hold: bool,
        chunkify: bool,
        br_name: Option<StrSlice<'a>>,
        br_code: i32,
    },
    ConfirmLong {
        title: StrSlice<'a>,
        pages: usize,
        br_code: i32,
    },
    Warning {
        title: StrSlice<'a>,
        content: StrSlice<'a>,
        verb: StrSlice<'a>,
        br_name: Option<StrSlice<'a>>,
        br_code: i32,
        allow_cancel: bool,
        danger: bool,
    },
    Mismatch {
        title: StrSlice<'a>,
        br_code: i32,
    },
    Danger {
        title: StrSlice<'a>,
        content: StrSlice<'a>,
        br_name: Option<StrSlice<'a>>,
        br_code: i32,
        verb_cancel: Option<StrSlice<'a>>,
        menu_title: Option<StrSlice<'a>>,
    },
    Success {
        title: StrSlice<'a>,
        content: StrSlice<'a>,
        button: StrSlice<'a>,
        duration_ms: Option<u32>,
        br_name: Option<StrSlice<'a>>,
        br_code: i32,
    },
    RequestNumber {
        title: StrSlice<'a>,
        content: StrSlice<'a>,
        initial: u32,
        min: u32,
        max: u32,
        br_code: i32,
    },
    ConfirmProperties {
        title: StrSlice<'a>,
        props: Slice<'a, Property<'a>>,
        subtitle: Option<StrSlice<'a>>,
        verb: Option<StrSlice<'a>>,
        hold: bool,
        br_name: Option<StrSlice<'a>>,
        br_code: i32,
    },
    ShowProperties {
        title: StrSlice<'a>,
        props: Slice<'a, Property<'a>>,
        subtitle: Option<StrSlice<'a>>,
        br_name: Option<StrSlice<'a>>,
        br_code: i32,
    },
    ShowPublicKey {
        pubkey: StrSlice<'a>,
        title: StrSlice<'a>,
        account: Option<StrSlice<'a>>,
        path: Option<StrSlice<'a>>,
        warning: Option<StrSlice<'a>>,
        br_name: StrSlice<'a>,
        br_code: i32,
    },
    ShowInfoWithCancel {
        title: StrSlice<'a>,
        items: Slice<'a, Property<'a>>,
        chunkify: bool,
        br_name: Option<StrSlice<'a>>,
        br_code: i32,
    },
    ConfirmWithInfo {
        title: StrSlice<'a>,
        subtitle: Option<StrSlice<'a>>,
        items: Slice<'a, StrExt<'a>>,
        verb: StrSlice<'a>,
        verb_info: Option<StrSlice<'a>>,
        br_name: Option<StrSlice<'a>>,
        br_code: i32,
    },
    ShowAddress {
        address: StrSlice<'a>,
        address_qr: StrSlice<'a>,
        title: Option<StrSlice<'a>>,
        subtitle: Option<StrSlice<'a>>,
        account: Option<StrSlice<'a>>,
        path: Option<StrSlice<'a>>,
        xpubs: Slice<'a, Property<'a>>,
        chunkify: bool,
        br_code: i32,
    },
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
    VerifyDerivationPath {
        address_n: Slice<'a, u32>,
        encoded_network: Option<Slice<'a, u8>>,
        encoded_token: Option<Slice<'a, u8>>,
        chain_id: Option<u64>,
    },
    GetEthPubkeyHash {
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
            Self::GetEthPubkeyHash { .. } => 1,
            Self::SignTypedHash { .. } => 2,
            Self::GetAddressMac { .. } => 3,
            Self::VerifyNonceCache { .. } => 4,
            Self::CheckAddressMac { .. } => 5,
            Self::VerifyDerivationPath { .. } => 6,
        }
    }
}

/// Result returned by the Core task after a crypto operation.
#[derive(Archive, Serialize, Deserialize)]
pub enum TrezorCryptoResult {
    Xpub(String<150>),
    Signature([u8; 65]),
    EthPubkeyHash([u8; 20]),
    AddressMac([u8; 32]),
    Boolean(bool),
}

// Internal utility message — used for requesting paginated content pages.
#[derive(Archive, Serialize, Deserialize)]
pub enum UtilEnum {
    RequestPage { idx: usize },
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

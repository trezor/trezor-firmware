#![no_std]

use rkyv::{
    munge::munge, rancor::Fallible, ser::Writer, Archive, ArchiveUnsized, Deserialize, Place,
    Portable, RelPtr, Serialize, SerializeUnsized,
};

/// Fixed-capacity byte string for `no_std`, serialized as `[u8; N] + len`.
#[derive(Archive, Serialize, Deserialize, Copy, Clone)]
pub struct String<const N: usize> {
    pub data: [u8; N],
    pub len: usize,
}

impl<const N: usize> String<N> {
    fn as_slice(&self) -> &[u8] {
        &self.data[..self.len]
    }

    pub fn as_str(&self) -> &str {
        // SAFETY: We ensure that the data up to `len` is always valid UTF-8 when creating a String.
        core::str::from_utf8(self.as_slice()).unwrap()
    }

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

type Prop<'a> = (StrSlice<'a>, StrSlice<'a>, bool);

#[derive(Archive, Serialize, Default)]
pub struct PropsList<'a> {
    pub data: [Prop<'a>; 5],
    pub len: u8,
}

impl<'a> PropsList<'a> {
    pub fn from_prop_slice(
        slice: &'a [(&'a str, &'a str, bool)],
    ) -> core::result::Result<Self, ()> {
        if slice.len() > 5 {
            return Err(());
        }

        let mut props = Self::default();
        for (key, value, is_mono) in slice {
            props.data[props.len as usize] =
                (StrSlice::from(*key), StrSlice::from(*value), *is_mono);
            props.len += 1;
        }
        Ok(props)
    }
}

#[derive(Archive, Serialize, Default)]
pub struct StrList<'a> {
    pub data: [StrSlice<'a>; 5],
    pub len: u8,
}

impl<'a> StrList<'a> {
    pub fn from_str_slice(slice: &'a [&'a str]) -> core::result::Result<Self, ()> {
        if slice.len() > 5 {
            return Err(());
        }

        let mut list = Self::default();
        for s in slice {
            list.data[list.len as usize] = StrSlice::from(*s);
            list.len += 1;
        }
        Ok(list)
    }
}

type StrExt<'a> = (StrSlice<'a>, bool);

#[derive(Archive, Serialize, Default)]
pub struct StrExtList<'a> {
    pub data: [StrExt<'a>; 5],
    pub len: u8,
}

impl<'a> StrExtList<'a> {
    pub fn from_str_slice(slice: &'a [(&'a str, bool)]) -> core::result::Result<Self, ()> {
        if slice.len() > 5 {
            return Err(());
        }

        let mut list = Self::default();
        for (s, flag) in slice {
            list.data[list.len as usize] = (StrSlice::from(*s), *flag);
            list.len += 1;
        }
        Ok(list)
    }
}

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
pub enum TrezorUiEnum<'a> {
    SelectMenu {
        items: StrList<'a>,
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
        hold: bool,
        verb: Option<StrSlice<'a>>,
        br_name: Option<StrSlice<'a>>,
        br_code: i32,
    },
    ConfirmSummary {
        title: StrSlice<'a>,
        amount: Option<StrSlice<'a>>,
        amount_label: Option<StrSlice<'a>>,
        fee: StrSlice<'a>,
        fee_label: StrSlice<'a>,
        account_title: Option<StrSlice<'a>>,
        account_items: Option<PropsList<'a>>,
        extra_title: Option<StrSlice<'a>>,
        extra_items: Option<PropsList<'a>>,
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
        warning_footer: Option<StrSlice<'a>>,
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
        props: PropsList<'a>,
        subtitle: Option<StrSlice<'a>>,
        verb: Option<StrSlice<'a>>,
        hold: bool,
        br_name: Option<StrSlice<'a>>,
        br_code: i32,
    },
    ShowProperties {
        title: StrSlice<'a>,
        props: PropsList<'a>,
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
        items: PropsList<'a>,
        chunkify: bool,
        br_name: Option<StrSlice<'a>>,
        br_code: i32,
    },
    ConfirmWithInfo {
        title: StrSlice<'a>,
        subtitle: Option<StrSlice<'a>>,
        items: StrExtList<'a>,
        verb: StrSlice<'a>,
        verb_info: StrSlice<'a>,
        br_name: Option<StrSlice<'a>>,
        br_code: i32,
    },
    ShowAddress {
        address: StrSlice<'a>,
        title: Option<StrSlice<'a>>,
        subtitle: Option<StrSlice<'a>>,
        account: Option<StrSlice<'a>>,
        path: Option<StrSlice<'a>>,
        xpubs: PropsList<'a>,
        chunkify: Option<bool>,
        br_code: i32,
    },
}

/// Outgoing UI result message for IPC
#[derive(Archive, Serialize, Deserialize)]
pub enum TrezorUiResult {
    Confirmed,
    Back,
    Cancelled,
    Info,
    Integer(u32),
}

#[derive(Archive, Serialize)]
pub enum TrezorCryptoEnum<'a> {
    GetXpub {
        address_n: Slice<'a, u32>,
    },
    GetEthPubkeyHash {
        address_n: Slice<'a, u32>,
        encoded_network: Option<Slice<'a, u8>>,
        encoded_token: Option<Slice<'a, u8>>,
    },
    SignTypedHash {
        address_n: Slice<'a, u32>,
        hash: [u8; 32],
        encoded_network: Option<Slice<'a, u8>>,
        encoded_token: Option<Slice<'a, u8>>,
        chain_id: Option<u64>,
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
        }
    }
}

/// Outgoing Crypto result message for IPC
#[derive(Archive, Serialize, Deserialize)]
pub enum TrezorCryptoResult {
    Xpub(String<150>), // (xpub bytes, xpub length)
    Signature([u8; 65]),
    EthPubkeyHash([u8; 20]),
    AddressMac([u8; 32]),
    Boolean(bool),
}

/// Outgoing Crypto result message for IPC
#[derive(Archive, Serialize, Deserialize)]
pub enum UtilEnum {
    RequestPage { idx: usize },
}

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

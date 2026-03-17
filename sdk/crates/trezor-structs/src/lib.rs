#![no_std]

use rkyv::{Archive, Deserialize, Serialize};

/// Fixed-capacity byte buffer for `no_std`, serialized as `[u8; N] + len`.
#[derive(Archive, Serialize, Deserialize, Copy, Clone)]
pub struct Buffer<const N: usize> {
    pub data: [u8; N],
    pub len: usize,
}

impl<const N: usize> Buffer<N> {
    pub fn as_slice(&self) -> &[u8] {
        &self.data[..self.len]
    }

    pub fn buf_from_slice(slice: &[u8]) -> core::result::Result<Self, ()> {
        if slice.len() > N {
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

pub type String<const N: usize> = Buffer<N>;

pub type ShortString = String<50>;
pub type LongString = String<150>;
pub type ExtraLongString = String<1030>;

pub type ShortBuffer = Buffer<100>;
pub type LongBuffer = Buffer<200>;

pub type ArchivedStringN<const N: usize> = rkyv::Archived<String<N>>;
pub type ArchivedShortString = rkyv::Archived<String<50>>;
pub type ArchivedLongString = rkyv::Archived<String<150>>;

pub type ArchivedBufferN<const N: usize> = rkyv::Archived<Buffer<N>>;
pub type ArchivedShortBuffer = rkyv::Archived<Buffer<100>>;
pub type ArchivedLongBuffer = rkyv::Archived<Buffer<200>>;

impl<const N: usize> String<N> {
    pub fn from_str(s: &str) -> core::result::Result<Self, ()> {
        if N > (usize::MAX as usize) || s.len() > N {
            return Err(());
        }

        let mut data = [0u8; N];
        data[..s.len()].copy_from_slice(s.as_bytes());
        Ok(Self { data, len: s.len() })
    }

    pub fn as_str(&self) -> &str {
        core::str::from_utf8(&self.data[..self.len]).unwrap_or("#INVALID#")
    }

    pub fn str_from_slice(slice: &[u8]) -> core::result::Result<Self, ()> {
        let s = core::str::from_utf8(slice).map_err(|_| ())?;
        Self::from_str(s)
    }
}

impl<const N: usize> AsRef<str> for String<N> {
    fn as_ref(&self) -> &str {
        core::str::from_utf8(&self.data[..self.len]).unwrap_or("#INVALID#")
    }
}

impl<const N: usize> Default for String<N> {
    fn default() -> Self {
        Self {
            data: [0u8; N],
            len: 0,
        }
    }
}

type Prop = (ShortString, ShortString, bool);

#[derive(Archive, Serialize)]
pub struct PropsList {
    pub data: [Prop; 5],
    pub len: u8,
}

impl Default for PropsList {
    fn default() -> Self {
        Self {
            data: [Prop::default(); 5],
            len: 0,
        }
    }
}

impl PropsList {
    pub fn from_prop_slice(slice: &[(&str, &str, bool)]) -> core::result::Result<Self, ()> {
        if slice.len() > 5 {
            return Err(());
        }

        let mut props = Self::default();
        for (key, value, is_mono) in slice {
            let key = ShortString::from_str(key)?;
            let value = ShortString::from_str(value)?;
            props.data[props.len as usize] = (key, value, *is_mono);
            props.len += 1;
        }
        Ok(props)
    }
}

#[derive(Archive, Serialize)]
pub struct StrList {
    pub data: [ShortString; 5],
    pub len: u8,
}

impl Default for StrList {
    fn default() -> Self {
        Self {
            data: [ShortString::default(); 5],
            len: 0,
        }
    }
}

impl StrList {
    pub fn from_str_slice(slice: &[&str]) -> core::result::Result<Self, ()> {
        if slice.len() > 5 {
            return Err(());
        }

        let mut list = Self::default();
        for s in slice {
            let s = ShortString::from_str(s)?;
            list.data[list.len as usize] = s;
            list.len += 1;
        }
        Ok(list)
    }
}

type StrExt = (ShortString, bool);

#[derive(Archive, Serialize)]
pub struct StrExtList {
    pub data: [StrExt; 5],
    pub len: u8,
}

impl Default for StrExtList {
    fn default() -> Self {
        Self {
            data: [StrExt::default(); 5],
            len: 0,
        }
    }
}

impl StrExtList {
    pub fn from_str_slice(slice: &[(&str, bool)]) -> core::result::Result<Self, ()> {
        if slice.len() > 5 {
            return Err(());
        }

        let mut list = Self::default();
        for (s, flag) in slice {
            let s = ShortString::from_str(s)?;
            list.data[list.len as usize] = (s, *flag);
            list.len += 1;
        }
        Ok(list)
    }
}

#[derive(Archive, Serialize, Default)]
pub struct DerivationPath {
    pub data: [u32; 8],
    pub len: u8,
}

impl DerivationPath {
    pub fn from_slice(slice: &[u32]) -> core::result::Result<Self, ()> {
        if slice.len() > 8 {
            return Err(());
        }
        let mut data = [0u32; 8];
        data[..slice.len()].copy_from_slice(slice);
        Ok(Self {
            data,
            len: slice.len() as u8,
        })
    }

    pub fn as_slice(&self) -> &[u32] {
        &self.data[..self.len as usize]
    }
}

#[derive(Default, Archive, Serialize)]
pub struct TypedHash {
    pub data: [u8; 32],
}

impl TypedHash {
    pub fn from_slice(slice: &[u8]) -> core::result::Result<Self, ()> {
        if slice.len() != 32 {
            return Err(());
        }
        let mut data = [0u8; 32];
        data.copy_from_slice(slice);
        Ok(Self { data })
    }

    pub fn as_slice(&self) -> &[u8] {
        &self.data
    }
}

#[derive(Archive, Serialize)]
pub enum TrezorUiEnum {
    SelectMenu {
        items: StrList,
        cancel: Option<ShortString>,
    },
    ConfirmAction {
        title: ShortString,
        action: ShortString,
        hold: bool,
    },
    ConfirmSummary {
        title: ShortString,
        amount: Option<ShortString>,
        amount_label: Option<ShortString>,
        fee: ShortString,
        fee_label: ShortString,
        account_title: Option<ShortString>,
        account_items: Option<PropsList>,
        extra_title: Option<ShortString>,
        extra_items: Option<PropsList>,
        back_button: bool,
        br_name: Option<ShortString>,
        br_code: i32,
    },
    ConfirmValue {
        title: ShortString,
        value: ExtraLongString,
        description: Option<ShortString>,
        is_data: bool,
        subtitle: Option<ShortString>,
        verb: Option<ShortString>,
        info: bool,
        hold: bool,
        chunkify: bool,
        page_counter: bool,
        cancel: bool,
        br_name: Option<ShortString>,
        br_code: i32,
        external_menu: bool,
    },
    ConfirmValueIntro {
        title: ShortString,
        value: ExtraLongString,
        subtitle: Option<ShortString>,
        verb: Option<ShortString>,
        verb_cancel: Option<ShortString>,
        hold: bool,
        chunkify: bool,
        br_name: Option<ShortString>,
        br_code: i32,
    },
    ConfirmLong {
        title: ShortString,
        pages: usize,
    },
    Warning {
        title: ShortString,
        content: ShortString,
        br_name: Option<ShortString>,
        br_code: i32,
    },
    Mismatch {
        title: ShortString,
    },
    Danger {
        title: ShortString,
        content: ShortString,
        br_name: Option<ShortString>,
        br_code: i32,
    },
    Success {
        title: ShortString,
        content: ShortString,
        button: ShortString,
        duration_ms: Option<u32>,
        br_name: Option<ShortString>,
    },
    RequestNumber {
        title: ShortString,
        content: ShortString,
        initial: u32,
        min: u32,
        max: u32,
    },
    ConfirmProperties {
        title: ShortString,
        props: PropsList,
        subtitle: Option<ShortString>,
        verb: Option<ShortString>,
        hold: bool,
        br_name: Option<ShortString>,
        br_code: i32,
    },
    ShowProperties {
        title: ShortString,
        props: PropsList,
        subtitle: Option<ShortString>,
        br_name: Option<ShortString>,
        br_code: i32,
    },
    ShowPublicKey {
        pubkey: LongString,
        title: Option<ShortString>,
        account: Option<ShortString>,
        path: Option<ShortString>,
        warning: Option<ShortString>,
        br_name: Option<ShortString>,
    },
    ShowInfoWithCancel {
        title: ShortString,
        items: PropsList,
        chunkify: bool,
        br_name: Option<ShortString>,
        br_code: i32,
    },
    ShouldShowMore {
        title: ShortString,
        items: StrExtList,
        button_text: ShortString,
        br_name: Option<ShortString>,
    },
    ShowAddress {
        address: ShortString,
        title: Option<ShortString>,
        subtitle: Option<ShortString>,
        account: Option<ShortString>,
        path: Option<ShortString>,
        xpubs: PropsList,
        chunkify: Option<bool>,
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
    String(ShortString),
}

#[derive(Archive, Serialize)]
pub enum TrezorCryptoEnum {
    GetXpub {
        address_n: DerivationPath,
    },
    GetEthPubkeyHash {
        address_n: DerivationPath,
        encoded_network: Option<ShortBuffer>,
        encoded_token: Option<ShortBuffer>,
    },
    SignTypedHash {
        address_n: DerivationPath,
        hash: TypedHash,
        encoded_network: Option<LongBuffer>,
        encoded_token: Option<LongBuffer>,
    },
    GetAddressMac {
        address_n: DerivationPath,
        address: ShortString,
        encoded_network: Option<ShortBuffer>,
    },
}

impl TrezorCryptoEnum {
    pub fn id(&self) -> u8 {
        match self {
            Self::GetXpub { .. } => 0,
            Self::GetEthPubkeyHash { .. } => 1,
            Self::SignTypedHash { .. } => 2,
            Self::GetAddressMac { .. } => 3,
        }
    }
}

/// Outgoing Crypto result message for IPC
#[derive(Archive, Serialize, Deserialize)]
pub enum TrezorCryptoResult {
    Xpub(LongString),
    Signature([u8; 65]),
    EthPubkeyHash([u8; 20]),
    AddressMac([u8; 32]),
    Failed(ShortString),
}

/// Outgoing Crypto result message for IPC
#[derive(Archive, Serialize, Deserialize)]
pub enum UtilEnum {
    RequestPage { idx: usize },
}

#[derive(Archive, Serialize, Deserialize)]
pub enum TrezorProgressEnum {
    Init {
        description: Option<ShortString>,
        title: Option<ShortString>,
        indeterminate: bool,
        danger: bool,
    },
    Update {
        description: Option<ShortString>,
        value: u32,
    },
    End,
}

impl TrezorProgressEnum {
    pub fn id(&self) -> u16 {
        match self {
            TrezorProgressEnum::Init { .. } => 0,
            TrezorProgressEnum::Update { .. } => 1,
            TrezorProgressEnum::End => 2,
        }
    }
}

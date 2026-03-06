#![no_std]

use rkyv::{Archive, Deserialize, Serialize};

/// Fixed-capacity byte buffer for `no_std`, serialized as `[u8; N] + len`.
#[derive(Archive, Serialize, Deserialize, Copy, Clone)]
pub struct Buffer<const N: usize> {
    pub data: [u8; N],
    pub len: usize,
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
    pub fn from_slice(slice: &[u8]) -> core::result::Result<Self, ()> {
        let s = core::str::from_utf8(slice).map_err(|_| ())?;
        Self::from_str(s)
    }

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

type Prop = (ShortString, ShortString);

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
    pub fn from_prop_slice(slice: &[(&str, &str)]) -> core::result::Result<Self, ()> {
        if slice.len() > 5 {
            return Err(());
        }

        let mut props = Self::default();
        for (key, value) in slice {
            let key = ShortString::from_str(key)?;
            let value = ShortString::from_str(value)?;
            props.data[props.len as usize] = (key, value);
            props.len += 1;
        }
        Ok(props)
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
    ConfirmAction {
        title: ShortString,
        action: ShortString,
        hold: bool,
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
        br_name: ShortString,
        br_code: u32,
    },
    ConfirmLong {
        title: ShortString,
        pages: usize,
    },
    Warning {
        title: ShortString,
        content: ShortString,
    },
    Mismatch {
        title: ShortString,
    },
    Danger {
        title: ShortString,
        content: ShortString,
    },
    Success {
        content: ShortString,
        br_name: ShortString,
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
    },
    ShowPublicKey {
        pubkey: LongString,
        title: Option<ShortString>,
        account: Option<ShortString>,
        path: Option<ShortString>,
        warning: Option<ShortString>,
        br_name: Option<ShortString>,
    },
    ShouldShowMore {
        title: ShortString,
        items: StrExtList,
        button_text: ShortString,
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
    ShowInfo {
        title: ShortString,
        items: PropsList,
        chunkify: bool,
    },
    ConfirmBlob {
        title: ShortString,
        data: ExtraLongString,
        hold: bool,
        chunkify: bool,
        verb: Option<ShortString>,
        verb_cancel: Option<ShortString>,
        is_data: bool,
        br_code: u32,
        br_name: ShortString,
    },
}

/// Outgoing UI result message for IPC
#[derive(Archive, Serialize, Deserialize)]
pub enum TrezorUiResult {
    None,
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
        encoded_network: Option<ShortBuffer>,
        encoded_token: Option<ShortBuffer>,
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
        description: ShortString,
        title: ShortString,
        indeterminate: bool,
        danger: bool,
    },
    Update {
        description: ShortString,
        value: u32,
    },
    End,
}

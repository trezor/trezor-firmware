#![no_std]

use rkyv::{Archive, Deserialize, Serialize};

/// Fixed-capacity UTF-8 string for `no_std`, serialized as `[u8; N] + len`.
#[derive(Archive, Serialize, Deserialize, Copy, Clone)]
pub struct String<const N: usize> {
    pub data: [u8; N],
    pub len: u8,
}

pub type ShortString = String<50>;
pub type LongString = String<150>;

pub type ArchivedStringN<const N: usize> = rkyv::Archived<String<N>>;
pub type ArchivedShortString = rkyv::Archived<String<50>>;
pub type ArchivedLongString = rkyv::Archived<String<150>>;

impl<const N: usize> String<N> {
    pub fn from_slice(slice: &[u8]) -> core::result::Result<Self, ()> {
        if N > (u8::MAX as usize) || slice.len() > N {
            return Err(());
        }
        let mut data = [0u8; N];
        data[..slice.len()].copy_from_slice(slice);
        Ok(Self {
            data,
            len: slice.len() as u8,
        })
    }

    pub fn from_str(s: &str) -> core::result::Result<Self, ()> {
        Self::from_slice(s.as_bytes())
    }

    pub fn as_str(&self) -> &str {
        core::str::from_utf8(&self.data[..self.len as usize]).unwrap_or("")
    }
}

impl<const N: usize> AsRef<str> for String<N> {
    fn as_ref(&self) -> &str {
        core::str::from_utf8(&self.data[..self.len as usize]).unwrap_or("#INVALID#")
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

#[derive(Archive, Serialize)]
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

impl Default for DerivationPath {
    fn default() -> Self {
        Self {
            data: [0u32; 8],
            len: 0,
        }
    }
}

#[derive(Archive, Serialize)]
pub enum TrezorUiEnum {
    ConfirmAction {
        title: ShortString,
        content: ShortString,
    },
    Warning {
        title: ShortString,
        content: ShortString,
    },
    Success {
        title: ShortString,
        content: ShortString,
    },
    RequestString {
        prompt: ShortString,
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
        key: LongString,
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
    SignHash {
        title: ShortString,
        content: ShortString,
    },
}

/// Outgoing Crypto result message for IPC
#[derive(Archive, Serialize, Deserialize)]
pub enum TrezorCryptoResult {
    None,
    Confirmed,
    Cancelled,
    Xpub(LongString),
    Signature([u8; 64]),
}

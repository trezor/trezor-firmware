#![no_std]

use rkyv::{Archive, Serialize};

/// Unified-length String type, long enough for most simple use-cases.
/// Stores the string as a fixed-size byte array with length for rkyv serialization.
#[derive(Archive, Serialize, Copy, Clone)]
pub struct ShortString {
    pub data: [u8; 50],
    pub len: u8,
}

pub type Prop = (ShortString, ShortString);

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

impl ShortString {
    pub fn from_slice(slice: &[u8]) -> core::result::Result<Self, ()> {
        if slice.len() > 50 {
            return Err(());
        }
        let mut data = [0u8; 50];
        data[..slice.len()].copy_from_slice(slice);
        Ok(Self {
            data,
            len: slice.len() as u8,
        })
    }

    pub fn from_str(s: &str) -> core::result::Result<Self, ()> {
        if s.len() > 50 {
            return Err(());
        }
        let mut data = [0u8; 50];
        data[..s.len()].copy_from_slice(s.as_bytes());
        Ok(Self {
            data,
            len: s.len() as u8,
        })
    }

    pub fn as_str(&self) -> &str {
        core::str::from_utf8(&self.data[..self.len as usize]).unwrap_or("")
    }
}

impl Default for ShortString {
    fn default() -> Self {
        Self {
            data: [0u8; 50],
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
}

/// Outgoing UI result message for IPC
#[derive(Archive, Serialize)]
pub enum TrezorUiResult {
    None,
    Confirmed,
    Back,
    Cancelled,
    Info,
    Integer(u32),
    String(ShortString),
}

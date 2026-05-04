#![allow(non_camel_case_types)]
#![allow(non_upper_case_globals)]
#![allow(dead_code)]

use micropython::{
    Obj,
    error::Error,
    qstr::{Attribute, QstrValue, try_from_obj},
};

impl const QstrValue for Qstr {
    fn from_u16(val: u16) -> Self {
        Self::from_u16(val)
    }

    fn to_u16(self) -> u16 {
        self.to_u16()
    }
}

impl Qstr {
    pub const fn to_obj(self) -> Obj {
        <Self as QstrValue>::to_obj(self)
    }

    pub const fn from_u16(val: u16) -> Self {
        Self(val as usize)
    }

    pub const fn to_u16(self) -> u16 {
        self.0 as u16
    }
}

impl TryFrom<Obj> for Qstr {
    type Error = Error;

    fn try_from(value: Obj) -> Result<Self, Self::Error> {
        try_from_obj(value)
    }
}

impl From<Attribute> for Qstr {
    fn from(value: Attribute) -> Self {
        Self::from_u16(value.into_raw() as u16)
    }
}

include!(concat!(env!("OUT_DIR"), "/qstr.rs"));

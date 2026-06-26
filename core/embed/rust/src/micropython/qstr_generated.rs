use super::{qstr, Obj};

#[allow(non_camel_case_types)]
#[allow(non_upper_case_globals)]
#[allow(dead_code)]
mod generated {
    include!(concat!(env!("OUT_DIR"), "/qstr.rs"));
}
pub use generated::Qstr;

// TODO: bindgen generates the Qstr type as usize, but for us it would be enough to have a u16

impl Qstr {
    pub const fn to_obj(self) -> Obj {
        <Self as qstr::QstrValue>::to_attribute(self).to_obj()
    }

    pub const fn from_u16(val: u16) -> Self {
        Self(val as _)
    }

    pub const fn to_u16(self) -> u16 {
        self.0 as u16
    }
}

impl const qstr::QstrValue for Qstr {
    fn from_u16(val: u16) -> Self {
        Self::from_u16(val)
    }

    fn to_u16(self) -> u16 {
        self.to_u16()
    }
}

impl TryFrom<Obj> for Qstr {
    type Error = super::Error;

    fn try_from(value: Obj) -> Result<Self, Self::Error> {
        qstr::try_from_obj(value)
    }
}

impl From<qstr::Attribute> for Qstr {
    fn from(value: qstr::Attribute) -> Self {
        Self::from_u16(value.into_raw() as u16)
    }
}

use core::{convert::TryFrom, slice, str::from_utf8};

use super::{ffi, Error, Obj};

pub const trait QstrValue: Copy {
    fn from_u16(val: u16) -> Self;
    fn to_u16(self) -> u16;

    fn to_attribute(self) -> Attribute {
        Attribute(self.to_u16() as _)
    }
}

pub trait QstrExt {
    fn as_str(self) -> &'static str;
}

impl<T: QstrValue> QstrExt for T {
    fn as_str(self) -> &'static str {
        self.to_attribute().as_str()
    }
}

pub fn try_from_obj<T: QstrValue>(obj: Obj) -> Result<T, Error> {
    if obj.is_qstr() {
        let attr = Attribute::from_obj_bits(obj.as_bits());
        Ok(T::from_u16(attr.into_raw() as _))
    } else {
        Err(Error::TypeError)
    }
}

impl<T: QstrValue> From<T> for Obj {
    fn from(value: T) -> Self {
        value.to_attribute().to_obj()
    }
}

#[derive(Debug, Copy, Clone, PartialEq, Eq, Hash)]
#[repr(transparent)]
pub struct Attribute(ffi::qstr);

impl Attribute {
    pub const fn into_raw(self) -> ffi::qstr {
        self.0
    }

    pub const fn from_raw(raw: ffi::qstr) -> Self {
        Self(raw)
    }

    pub const fn from_u16(val: u16) -> Self {
        Self(val as _)
    }

    pub fn as_str(self) -> &'static str {
        let mut len = 0usize;
        let slice = unsafe {
            // SAFETY: qstr_data should always return a valid string, even for unknown ids.
            let ptr = ffi::qstr_data(self.0, &mut len as *mut _);
            slice::from_raw_parts(ptr, len)
        };
        // SAFETY: Qstr pools are either ROM-based or permanently allocated in the GC
        // arena. The MicroPython runtime holds the respective head pointers so we don't
        // need to care.
        unwrap!(from_utf8(slice))
    }

    pub const fn to_obj(self) -> Obj {
        // SAFETY:
        //  - Micropython compiled with `MICROPY_OBJ_REPR == MICROPY_OBJ_REPR_A`.
        //    micropython/py/obj.h #define MP_OBJ_NEW_QSTR(qst)
        //    ((mp_obj_t)((((mp_uint_t)(qst)) << 3) | 2))
        let bits = ((self.0 as usize) << 3) | 2;
        unsafe { Obj::from_bits(bits) }
    }

    pub(crate) const fn from_obj_bits(bits: cty::uintptr_t) -> Self {
        let bits = (bits >> 3) as u16; // See `Self::to_obj`.
        Self::from_u16(bits)
    }

    pub const fn from_qstr_value<T: const QstrValue>(value: T) -> Self {
        Self::from_u16(value.to_u16())
    }
}

impl From<Attribute> for Obj {
    fn from(value: Attribute) -> Self {
        value.to_obj()
    }
}

impl TryFrom<Obj> for Attribute {
    type Error = Error;

    fn try_from(value: Obj) -> Result<Self, Self::Error> {
        if value.is_qstr() {
            Ok(Self::from_obj_bits(value.as_bits()))
        } else {
            Err(Error::TypeError)
        }
    }
}

#[inline]
pub const fn qstr_value_to_u16<T: const QstrValue>(value: T) -> u16 {
    value.to_u16()
}

// XXX compatibility re-export
// The intention here is that after the crate split, `crate::micropython::qstr::Qstr` remains valid
pub use super::qstr_generated::Qstr;

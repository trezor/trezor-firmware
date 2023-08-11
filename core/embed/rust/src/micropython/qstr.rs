#![allow(non_camel_case_types)]
#![allow(non_upper_case_globals)]
#![allow(dead_code)]

use core::{convert::TryFrom, slice, str::from_utf8};

use crate::error::Error;

use super::{ffi, obj::Obj};

impl Qstr {
    pub const fn to_obj(self) -> Obj {
        // SAFETY:
        //  - Micropython compiled with `MICROPY_OBJ_REPR == MICROPY_OBJ_REPR_A`.
        //    micropython/py/obj.h #define MP_OBJ_NEW_QSTR(qst)
        //    ((mp_obj_t)((((mp_uint_t)(qst)) << 3) | 2))
        let bits = (self.0 << 3) | 2;
        unsafe { Obj::from_bits(bits) }
    }

    pub const fn from_obj_bits(bits: cty::uintptr_t) -> Self {
        let bits = (bits >> 3) as u16; // See `Self::to_obj`.
        Self::from_u16(bits)
    }

    pub const fn to_u16(self) -> u16 {
        // TODO: Change the internal representation of Qstr to u16.
        self.0 as _
    }

    pub const fn from_u16(val: u16) -> Self {
        // TODO: Change the internal representation of Qstr to u16.
        Self(val as _)
    }

    pub fn as_str(self) -> &'static str {
        let mut len = 0usize;
        let slice = unsafe {
            // SAFETY: qstr_data should always return a valid string, even for unknown ids.
            let ptr = ffi::qstr_data(self.0 as _, &mut len as *mut _);
            slice::from_raw_parts(ptr, len)
        };
        // SAFETY: Qstr pools are either ROM-based or permanently allocated in the GC
        // arena. The MicroPython runtime holds the respective head pointers so we don't
        // need to care.
        unwrap!(from_utf8(slice))
    }
}

impl From<u16> for Qstr {
    fn from(val: u16) -> Self {
        Self::from_u16(val)
    }
}

impl TryFrom<Obj> for Qstr {
    type Error = Error;

    fn try_from(value: Obj) -> Result<Self, Self::Error> {
        if value.is_qstr() {
            Ok(Self::from_obj_bits(value.as_bits()))
        } else {
            Err(Error::TypeError)
        }
    }
}

impl From<Qstr> for Obj {
    fn from(value: Qstr) -> Self {
        value.to_obj()
    }
}

include!(concat!(env!("OUT_DIR"), "/qstr.rs"));

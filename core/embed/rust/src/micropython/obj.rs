use core::convert::{TryFrom, TryInto};
use core::num::TryFromIntError;

use crate::error::Error;

use super::ffi;

pub type Obj = ffi::mp_obj_t;
pub type ObjBase = ffi::mp_obj_base_t;

impl PartialEq for Obj {
    fn eq(&self, other: &Self) -> bool {
        self.as_bits() == other.as_bits()
    }
}

impl Eq for Obj {}

impl Obj {
    pub const unsafe fn from_ptr(ptr: *mut cty::c_void) -> Self {
        Self(ptr)
    }

    pub const fn as_ptr(self) -> *mut cty::c_void {
        self.0
    }

    pub const unsafe fn from_bits(bits: cty::uintptr_t) -> Self {
        Self(bits as _)
    }

    pub fn as_bits(self) -> cty::uintptr_t {
        self.0 as _
    }
}

impl Obj {
    pub fn is_small_int(self) -> bool {
        self.as_bits() & 1 != 0
    }

    pub fn is_qstr(self) -> bool {
        self.as_bits() & 7 == 2
    }

    pub fn is_immediate(self) -> bool {
        self.as_bits() & 7 == 6
    }

    pub fn is_ptr(self) -> bool {
        self.as_bits() & 3 == 0
    }
}

impl Obj {
    pub const fn const_null() -> Self {
        // micropython/py/obj.h
        // #define MP_OBJ_NULL (MP_OBJ_FROM_PTR((void *)0))
        unsafe { Self::from_bits(0) }
    }

    pub const fn const_stop_iteration() -> Self {
        // micropython/py/obj.h
        // #define MP_OBJ_STOP_ITERATION (MP_OBJ_FROM_PTR((void *)0))
        unsafe { Self::from_bits(0) }
    }

    pub const fn const_none() -> Self {
        // micropython/py/obj.h
        // #define mp_const_none MP_OBJ_NEW_IMMEDIATE_OBJ(0)
        unsafe { Self::immediate(0) }
    }

    pub const fn const_false() -> Self {
        // micropython/py/obj.h
        // #define mp_const_false MP_OBJ_NEW_IMMEDIATE_OBJ(1)
        unsafe { Self::immediate(1) }
    }

    pub const fn const_true() -> Self {
        // micropython/py/obj.h
        // #define mp_const_true MP_OBJ_NEW_IMMEDIATE_OBJ(3)
        unsafe { Self::immediate(3) }
    }

    const unsafe fn immediate(val: usize) -> Self {
        // SAFETY:
        //  - `val` is in `0..=3` range.
        //  - Micropython compiled with `MICROPY_OBJ_REPR == MICROPY_OBJ_REPR_A`.
        //  - Micropython compiled with `MICROPY_OBJ_IMMEDIATE_OBJS`.
        //    micropython/py/obj.h #define MP_OBJ_NEW_IMMEDIATE_OBJ(val)
        //    ((mp_obj_t)(((val) << 3) | 6))
        Self::from_bits((val << 3) | 6)
    }
}

impl Obj {
    pub fn call_with_n_args(self, args: &[Obj]) -> Obj {
        // SAFETY:
        //  - Can call python code and therefore raise.
        //  - Each of `args` has no lifetime bounds.
        unsafe { ffi::mp_call_function_n_kw(self, args.len(), 0, args.as_ptr()) }
    }
}

impl TryFrom<Obj> for bool {
    type Error = Error;

    fn try_from(obj: Obj) -> Result<Self, Self::Error> {
        // TODO: Avoid type casts on the Python side.
        // SAFETY:
        //  - Can call python code and therefore raise.
        if unsafe { ffi::mp_obj_is_true(obj) } {
            Ok(true)
        } else {
            Ok(false)
        }
    }
}

impl TryInto<Obj> for isize {
    type Error = Error;

    fn try_into(self) -> Result<Obj, Self::Error> {
        let int = ffi::mp_int_t::try_from(self)?;
        // SAFETY:
        //  - Can raise if allocation fails.
        let obj = unsafe { ffi::mp_obj_new_int(int) };
        Ok(obj)
    }
}

impl TryFrom<Obj> for isize {
    type Error = Error;

    fn try_from(obj: Obj) -> Result<Self, Self::Error> {
        let mut int: ffi::mp_int_t = 0;

        // TODO: Avoid type casts on the Python side.
        // SAFETY:
        //  - Can raise if `arg` is int but cannot fit into `cty::uintptr_t`.
        if unsafe { ffi::mp_obj_get_int_maybe(obj.as_ptr(), &mut int) } {
            let int = int.try_into()?;
            Ok(int)
        } else {
            Err(Error::NotInt)
        }
    }
}

impl TryInto<Obj> for &[u8] {
    type Error = Error;

    fn try_into(self) -> Result<Obj, Self::Error> {
        // SAFETY:
        //  - Can raise if allocation fails.
        let obj = unsafe { ffi::mp_obj_new_bytes(self.as_ptr(), self.len()) };
        Ok(obj)
    }
}

//
// Additional conversions based on the methods above.
//

impl TryInto<Obj> for u8 {
    type Error = Error;

    fn try_into(self) -> Result<Obj, Self::Error> {
        let int = isize::from(self);
        let obj = int.try_into()?;
        Ok(obj)
    }
}

impl TryInto<Obj> for u16 {
    type Error = Error;

    fn try_into(self) -> Result<Obj, Self::Error> {
        let int = isize::try_from(self)?;
        let obj = int.try_into()?;
        Ok(obj)
    }
}

impl TryInto<Obj> for u32 {
    type Error = Error;

    fn try_into(self) -> Result<Obj, Self::Error> {
        let int = isize::try_from(self)?;
        let obj = int.try_into()?;
        Ok(obj)
    }
}

impl TryInto<Obj> for usize {
    type Error = Error;

    fn try_into(self) -> Result<Obj, Self::Error> {
        let int = isize::try_from(self)?;
        let obj = int.try_into()?;
        Ok(obj)
    }
}

impl TryInto<Obj> for i32 {
    type Error = Error;

    fn try_into(self) -> Result<Obj, Self::Error> {
        let int = isize::try_from(self)?;
        let obj = int.try_into()?;
        Ok(obj)
    }
}

impl TryFrom<Obj> for u8 {
    type Error = Error;

    fn try_from(obj: Obj) -> Result<Self, Self::Error> {
        let int = isize::try_from(obj)?;
        let this = Self::try_from(int)?;
        Ok(this)
    }
}

impl TryFrom<Obj> for u16 {
    type Error = Error;

    fn try_from(obj: Obj) -> Result<Self, Self::Error> {
        let int = isize::try_from(obj)?;
        let this = Self::try_from(int)?;
        Ok(this)
    }
}

impl TryFrom<Obj> for u32 {
    type Error = Error;

    fn try_from(obj: Obj) -> Result<Self, Self::Error> {
        let int = isize::try_from(obj)?;
        let this = Self::try_from(int)?;
        Ok(this)
    }
}

impl TryFrom<Obj> for usize {
    type Error = Error;

    fn try_from(obj: Obj) -> Result<Self, Self::Error> {
        let int = isize::try_from(obj)?;
        let this = Self::try_from(int)?;
        Ok(this)
    }
}

impl TryFrom<Obj> for i32 {
    type Error = Error;

    fn try_from(obj: Obj) -> Result<Self, Self::Error> {
        let int = isize::try_from(obj)?;
        let this = Self::try_from(int)?;
        Ok(this)
    }
}

impl From<TryFromIntError> for Error {
    fn from(_: TryFromIntError) -> Self {
        Self::OutOfRange
    }
}

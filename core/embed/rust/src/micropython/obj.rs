use core::convert::{TryFrom, TryInto};

use crate::error::Error;

// micropython/py/obj.h mp_obj_t
#[repr(transparent)]
#[derive(Copy, Clone, Eq, PartialEq)]
pub struct Obj(cty::uintptr_t);

extern "C" {
    // micropython/py/obj.h
    // Can raise if allocation fails.
    fn mp_obj_new_int(value: cty::intptr_t) -> Obj;

    // micropython/py/objstr.h
    // Can raise if allocation fails.
    fn mp_obj_new_bytes(data: *const u8, len: usize) -> Obj;

    // micropython/py/obj.h
    // Can raise if `arg` is int but cannot fit into `cty::uintptr_t`.
    fn mp_obj_get_int_maybe(arg: Obj, value: *mut cty::intptr_t) -> bool;

    // micropython/py/obj.h
    // Can call python code and therefore raise.
    fn mp_obj_is_true(arg: Obj) -> bool;

    // micropython/py/runtime.h
    // Can call python code and therefore raise.
    fn mp_call_function_n_kw(fun: Obj, n_args: usize, n_kw: usize, args: *const Obj) -> Obj;
}

impl Obj {
    pub unsafe fn from_raw(bits: usize) -> Self {
        Self(bits)
    }

    pub fn const_null() -> Self {
        // micropython/py/obj.h
        // #define MP_OBJ_NULL (MP_OBJ_FROM_PTR((void *)0))
        unsafe { Self::from_raw(0) }
    }

    pub fn const_stop_iteration() -> Self {
        // micropython/py/obj.h
        // #define MP_OBJ_STOP_ITERATION (MP_OBJ_FROM_PTR((void *)0))
        unsafe { Self::from_raw(0) }
    }

    pub fn const_none() -> Self {
        // micropython/py/obj.h
        // #define mp_const_none MP_OBJ_NEW_IMMEDIATE_OBJ(0)
        unsafe { Self::immediate(0) }
    }

    pub fn const_false() -> Self {
        // micropython/py/obj.h
        // #define mp_const_false MP_OBJ_NEW_IMMEDIATE_OBJ(1)
        unsafe { Self::immediate(1) }
    }

    pub fn const_true() -> Self {
        // micropython/py/obj.h
        // #define mp_const_true MP_OBJ_NEW_IMMEDIATE_OBJ(3)
        unsafe { Self::immediate(3) }
    }

    unsafe fn immediate(val: usize) -> Self {
        // SAFETY:
        //  - `val` is in `0..=3` range.
        //  - Micropython compiled with `MICROPY_OBJ_REPR == MICROPY_OBJ_REPR_A`.
        //  - Micropython compiled with `MICROPY_OBJ_IMMEDIATE_OBJS`.
        //    micropython/py/obj.h #define MP_OBJ_NEW_IMMEDIATE_OBJ(val)
        //    ((mp_obj_t)(((val) << 3) | 6))
        Self::from_raw((val << 3) | 6)
    }

    pub fn call_with_n_args(&self, args: &[Obj]) -> Obj {
        // SAFETY:
        //  - `mp_call_function_n_kw` binding corresponds to the C source.
        //  - Each of `args` has no lifetime bounds.
        unsafe { mp_call_function_n_kw(*self, args.len(), 0, args.as_ptr()) }
    }
}

impl TryInto<Obj> for isize {
    type Error = Error;

    fn try_into(self) -> Result<Obj, Self::Error> {
        let int = cty::intptr_t::try_from(self).map_err(|_| Error::OutOfRange)?;
        // SAFETY:
        //  - `mp_obj_new_int` binding corresponds to the C source.
        let obj = unsafe { mp_obj_new_int(int) };
        Ok(obj)
    }
}

impl TryInto<Obj> for usize {
    type Error = Error;

    fn try_into(self) -> Result<Obj, Self::Error> {
        let int = isize::try_from(self).map_err(|_| Error::OutOfRange)?;
        let obj = int.try_into()?;
        Ok(obj)
    }
}

impl TryInto<Obj> for &[u8] {
    type Error = Error;

    fn try_into(self) -> Result<Obj, Self::Error> {
        // SAFETY:
        //  - `mp_obj_new_bytes` binding corresponds to the C source.
        let obj = unsafe { mp_obj_new_bytes(self.as_ptr(), self.len()) };
        Ok(obj)
    }
}

impl TryFrom<Obj> for isize {
    type Error = Error;

    fn try_from(obj: Obj) -> Result<Self, Self::Error> {
        let mut int: cty::intptr_t = 0;

        // TODO: Avoid type casts on the Python side.
        // SAFETY:
        //  - `mp_obj_get_int_maybe` binding corresponds to the C source.
        if unsafe { mp_obj_get_int_maybe(obj, &mut int as _) } {
            Ok(int)
        } else {
            Err(Error::NotInt)
        }
    }
}

impl TryFrom<Obj> for u16 {
    type Error = Error;

    fn try_from(obj: Obj) -> Result<Self, Self::Error> {
        let int = isize::try_from(obj)?;
        let this = u16::try_from(int).map_err(|_| Error::OutOfRange)?;
        Ok(this)
    }
}

impl TryFrom<Obj> for u32 {
    type Error = Error;

    fn try_from(obj: Obj) -> Result<Self, Self::Error> {
        let int = isize::try_from(obj)?;
        let this = u32::try_from(int).map_err(|_| Error::OutOfRange)?;
        Ok(this)
    }
}

impl TryFrom<Obj> for usize {
    type Error = Error;

    fn try_from(obj: Obj) -> Result<Self, Self::Error> {
        let int = isize::try_from(obj)?;
        let this = usize::try_from(int).map_err(|_| Error::OutOfRange)?;
        Ok(this)
    }
}

impl TryFrom<Obj> for i32 {
    type Error = Error;

    fn try_from(obj: Obj) -> Result<Self, Self::Error> {
        let int = isize::try_from(obj)?;
        let this = i32::try_from(int).map_err(|_| Error::OutOfRange)?;
        Ok(this)
    }
}

impl TryFrom<Obj> for bool {
    type Error = Error;

    fn try_from(obj: Obj) -> Result<Self, Self::Error> {
        // TODO: Avoid type casts on the Python side.
        // SAFETY:
        //  - `mp_obj_is_true` binding corresponds to the C source.
        if unsafe { mp_obj_is_true(obj) } {
            Ok(true)
        } else {
            Ok(false)
        }
    }
}

use core::{
    convert::{TryFrom, TryInto},
    num::TryFromIntError,
};

use cstr_core::CStr;

use crate::error::Error;

use super::{ffi, runtime::catch_exception};

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
        // micropython/py/obj.h mp_obj_is_small_int
        self.as_bits() & 1 != 0
    }

    pub fn is_qstr(self) -> bool {
        // micropython/py/obj.h mp_obj_is_qstr
        self.as_bits() & 7 == 2
    }

    pub fn is_immediate(self) -> bool {
        // micropython/py/obj.h mp_obj_is_immediate_obj
        self.as_bits() & 7 == 6
    }

    pub fn is_ptr(self) -> bool {
        // micropython/py/obj.h mp_obj_is_obj
        self.as_bits() & 3 == 0
    }

    pub fn is_null(self) -> bool {
        // obj == NULL
        self.as_bits() == 0
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
        //  - MicroPython compiled with `MICROPY_OBJ_REPR == MICROPY_OBJ_REPR_A`.
        //  - MicroPython compiled with `MICROPY_OBJ_IMMEDIATE_OBJS`.
        //    micropython/py/obj.h #define MP_OBJ_NEW_IMMEDIATE_OBJ(val)
        //    ((mp_obj_t)(((val) << 3) | 6))
        unsafe { Self::from_bits((val << 3) | 6) }
    }
}

impl Obj {
    pub fn call_with_n_args(self, args: &[Obj]) -> Result<Obj, Error> {
        // SAFETY:
        //  - Each of `args` has no lifetime bounds.
        // EXCEPTION: Calls Python code so can raise arbitrarily.
        catch_exception(|| unsafe {
            ffi::mp_call_function_n_kw(self, args.len(), 0, args.as_ptr())
        })
    }
}

//
// # Converting `Obj` into plain data.
//

impl TryFrom<Obj> for bool {
    type Error = Error;

    fn try_from(obj: Obj) -> Result<Self, Self::Error> {
        // TODO: Avoid type casts on the Python side.
        // SAFETY:
        //  - `obj` can be anything uPy understands.
        // EXCEPTION: Can call Python code (on custom instances) and therefore raise.
        let is_true = catch_exception(|| unsafe { ffi::mp_obj_is_true(obj) })?;
        Ok(is_true)
    }
}

impl TryFrom<Obj> for i32 {
    type Error = Error;

    fn try_from(obj: Obj) -> Result<Self, Self::Error> {
        let mut int: ffi::mp_int_t = 0;

        // TODO: Avoid type casts on the Python side.
        // SAFETY:
        //  - `int` is a mutable pointer of the right type.
        //  - `obj` can be anything uPy understands.
        // EXCEPTION: Can raise if `obj` is int but cannot fit into `cty::mp_int_t`.
        let result =
            catch_exception(|| unsafe { ffi::mp_obj_get_int_maybe(obj.as_ptr(), &mut int) })?;
        if result {
            Ok(int.try_into()?)
        } else {
            Err(Error::TypeError)
        }
    }
}

impl TryFrom<Obj> for i64 {
    type Error = Error;

    fn try_from(obj: Obj) -> Result<Self, Self::Error> {
        let mut ll: cty::c_longlong = 0;

        // SAFETY:
        //  - `ll` is a mutable variable of the right type.
        //  - `obj` can be anything uPy understands.
        // EXCEPTION: Does not raise.
        if unsafe { ffi::trezor_obj_get_ll_checked(obj, &mut ll) } {
            Ok(ll)
        } else {
            Err(Error::TypeError)
        }
    }
}

//
// # Converting plain data into `Obj`.
//

impl From<bool> for Obj {
    fn from(val: bool) -> Self {
        if val {
            Obj::const_true()
        } else {
            Obj::const_false()
        }
    }
}

impl TryFrom<i32> for Obj {
    type Error = Error;

    fn try_from(val: i32) -> Result<Self, Self::Error> {
        // `mp_obj_new_int` accepts a `mp_int_t` argument, which is word-sized. We
        // primarily target 32-bit architecture, and therefore keep the primary signed
        // conversion type as `i32`, but convert through `into()` if the types differ.

        // EXCEPTION: Can raise if `val` is larger than smallint and allocation fails.
        catch_exception(|| unsafe { ffi::mp_obj_new_int(val.into()) })
    }
}

impl TryFrom<i64> for Obj {
    type Error = Error;

    fn try_from(val: i64) -> Result<Self, Self::Error> {
        // Because `mp_obj_new_int_from_ll` allocates even if `val` fits into small-int,
        // we try to go through `mp_obj_new_int` first.
        match i32::try_from(val) {
            Ok(smaller_val) => smaller_val.try_into(),
            // EXCEPTION: Will raise if allocation fails.
            Err(_) => catch_exception(|| unsafe { ffi::mp_obj_new_int_from_ll(val) }),
        }
    }
}

impl TryFrom<u32> for Obj {
    type Error = Error;

    fn try_from(val: u32) -> Result<Self, Self::Error> {
        // `mp_obj_new_int_from_uint` accepts a `mp_uint_t` argument, which is
        // word-sized. We primarily target 32-bit architecture, and therefore keep
        // the primary unsigned conversion type as `u32`, but convert through `into()`
        // if the types differ.

        // EXCEPTION: Can raise if `val` is larger than smallint and allocation fails.
        catch_exception(|| unsafe { ffi::mp_obj_new_int_from_uint(val.into()) })
    }
}

impl TryFrom<u64> for Obj {
    type Error = Error;

    fn try_from(val: u64) -> Result<Self, Self::Error> {
        // Because `mp_obj_new_int_from_ull` allocates even if `val` fits into
        // small-int, we try to go through `mp_obj_new_int_from_uint` first.
        match u32::try_from(val) {
            Ok(smaller_val) => smaller_val.try_into(),
            // EXCEPTION: Will raise if allocation fails.
            Err(_) => catch_exception(|| unsafe { ffi::mp_obj_new_int_from_ull(val) }),
        }
    }
}

/// Byte slices are converted into `bytes` MicroPython objects, by allocating
/// new space on the heap and copying.
impl TryFrom<&[u8]> for Obj {
    type Error = Error;

    fn try_from(val: &[u8]) -> Result<Self, Self::Error> {
        // SAFETY:
        //  - Should work with any data
        // EXCEPTION: Will raise if allocation fails.
        catch_exception(|| unsafe { ffi::mp_obj_new_bytes(val.as_ptr(), val.len()) })
    }
}

/// String slices are converted into `str` MicroPython objects. Strings that are
/// already interned will turn up as QSTRs, strings not found in the QSTR pool
/// will be allocated on the heap and copied.
impl TryFrom<&str> for Obj {
    type Error = Error;

    fn try_from(val: &str) -> Result<Self, Self::Error> {
        // SAFETY:
        //  - `str` is guaranteed to be UTF-8.
        // EXCEPTION: Will raise if allocation fails.
        catch_exception(|| unsafe { ffi::mp_obj_new_str(val.as_ptr().cast(), val.len()) })
    }
}

/// ROM null-terminated strings can be converted to `str` MicroPython objects
/// without making a copy on the heap, only allocating the `mp_obj_str_t`
/// struct.
impl TryFrom<&'static CStr> for Obj {
    type Error = Error;

    fn try_from(val: &'static CStr) -> Result<Self, Self::Error> {
        // SAFETY:
        //  - `CStr` is guaranteed to be null-terminated UTF-8.
        //  - the argument is static so it will remain valid for the lifetime of result.
        let obj = unsafe { ffi::trezor_obj_str_from_rom_text(val.as_ptr()) };
        if obj.is_null() {
            Err(Error::AllocationFailed)
        } else {
            Ok(obj)
        }
    }
}

//
// # Additional conversions based on the methods above.
//

impl From<u8> for Obj {
    fn from(val: u8) -> Self {
        // `u8` will fit into smallint so no error should happen here.
        u32::from(val).try_into().unwrap()
    }
}

impl From<u16> for Obj {
    fn from(val: u16) -> Self {
        // `u16` will fit into smallint so no error should happen here.
        u32::from(val).try_into().unwrap()
    }
}

impl TryFrom<usize> for Obj {
    type Error = Error;

    fn try_from(val: usize) -> Result<Self, Self::Error> {
        // Willingly truncate the bits on 128-bit architectures.
        (val as u64).try_into()
    }
}

impl TryFrom<Obj> for u8 {
    type Error = Error;

    fn try_from(obj: Obj) -> Result<Self, Self::Error> {
        let val = i32::try_from(obj)?;
        let this = Self::try_from(val)?;
        Ok(this)
    }
}

impl TryFrom<Obj> for u16 {
    type Error = Error;

    fn try_from(obj: Obj) -> Result<Self, Self::Error> {
        let val = i32::try_from(obj)?;
        let this = Self::try_from(val)?;
        Ok(this)
    }
}

impl TryFrom<Obj> for u32 {
    type Error = Error;

    fn try_from(obj: Obj) -> Result<Self, Self::Error> {
        let val = i64::try_from(obj)?;
        let this = Self::try_from(val)?;
        Ok(this)
    }
}

impl TryFrom<Obj> for u64 {
    type Error = Error;

    fn try_from(obj: Obj) -> Result<Self, Self::Error> {
        // TODO: Support full range.
        let val = i64::try_from(obj)?;
        let this = Self::try_from(val)?;
        Ok(this)
    }
}

impl TryFrom<Obj> for usize {
    type Error = Error;

    fn try_from(obj: Obj) -> Result<Self, Self::Error> {
        // TODO: Support full range.
        let val = i64::try_from(obj)?;
        let this = Self::try_from(val)?;
        Ok(this)
    }
}

impl<T> From<Option<T>> for Obj
where
    T: Into<Obj>,
{
    fn from(val: Option<T>) -> Self {
        match val {
            Some(v) => v.into(),
            None => Self::const_none(),
        }
    }
}

impl Obj {
    /// Conversion to Rust types with typed `None`.
    pub fn try_into_option<T>(self) -> Result<Option<T>, Error>
    where
        T: TryFrom<Obj>,
        <T as TryFrom<Obj>>::Error: Into<Error>,
    {
        if self == Obj::const_none() {
            return Ok(None);
        }
        match self.try_into() {
            Ok(x) => Ok(Some(x)),
            Err(e) => Err(e.into()),
        }
    }
}

impl From<TryFromIntError> for Error {
    fn from(_: TryFromIntError) -> Self {
        Self::OutOfRange
    }
}

use core::ops::Deref;

use super::ffi;
use super::obj::{Obj, ObjBase};

pub type Type = ffi::mp_obj_type_t;

impl Type {
    pub fn is_type_of(&'static self, obj: Obj) -> bool {
        match obj.type_() {
            Some(type_) => core::ptr::eq(type_, self),
            None => false,
        }
    }

    pub const fn as_base(&'static self) -> ObjBase {
        ObjBase { type_: self }
    }

    pub const fn as_obj(&'static self) -> Obj {
        // SAFETY:
        //  - We are an object struct with a base and a type.
        //  - 'static lifetime holds us in place.
        //  - MicroPython is smart enough not to mutate `mp_obj_type_t` objects.
        unsafe { Obj::from_ptr(self as *const _ as *mut _) }
    }

    #[cfg(any(feature = "debug", feature = "dbg_console"))]
    pub fn name(&self) -> &'static str {
        use super::qstr::Qstr;

        Qstr::from(self.name).as_str()
    }
}

// SAFETY: We are in a single-threaded environment.
unsafe impl Sync for Type {}

/// Since Type has variable size due to its slots array, functions that
/// construct type objects return this which is a Type with the maximum number
/// of slots.
pub type FullType = ffi::mp_obj_full_type_t;

impl FullType {
    pub const fn as_type(&self) -> &Type {
        let type_ptr = self as *const Self as *const ffi::mp_obj_type_t;
        // SAFETY:
        //  - aligned, non-null, and dereferanceable because it came from a reference
        //  - pointee is valid because the initial part of FullType has the same layout
        //    as Type
        //  - aliasing the same as source reference
        unsafe { type_ptr.as_ref_unchecked() }
    }
}

impl Deref for FullType {
    type Target = Type;

    fn deref(&self) -> &Type {
        self.as_type()
    }
}

// SAFETY: We are in a single-threaded environment.
unsafe impl Sync for FullType {}

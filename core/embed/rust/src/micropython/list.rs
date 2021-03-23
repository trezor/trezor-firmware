use core::convert::TryFrom;

use crate::error::Error;

use super::{ffi, gc::Gc, obj::Obj};

pub type List = ffi::mp_obj_list_t;

impl List {
    pub fn alloc(values: &[Obj]) -> Gc<Self> {
        // SAFETY: Altough `values` are copied into the new list and not mutated,
        // `mp_obj_new_list` is taking them through a mut pointer.
        unsafe {
            let list = ffi::mp_obj_new_list(values.len(), values.as_ptr() as *mut Obj);
            Gc::from_raw(list.as_ptr().cast())
        }
    }

    pub fn append(&mut self, value: Obj) {
        unsafe {
            let ptr = self as *mut Self;
            let list = Obj::from_ptr(ptr.cast());
            ffi::mp_obj_list_append(list, value);
        }
    }
}

impl From<Gc<List>> for Obj {
    fn from(value: Gc<List>) -> Self {
        // SAFETY:
        //  - `value` is an object struct with a base and a type.
        //  - `value` is GC-allocated.
        unsafe { Obj::from_ptr(Gc::into_raw(value).cast()) }
    }
}

impl TryFrom<Obj> for Gc<List> {
    type Error = Error;

    fn try_from(value: Obj) -> Result<Self, Self::Error> {
        if unsafe { ffi::mp_type_list.is_type_of(value) } {
            // SAFETY: We assume that if `value` is an object pointer with the correct type,
            // it is managed by MicroPython GC (see `Gc::from_raw` for details).
            let this = unsafe { Gc::from_raw(value.as_ptr().cast()) };
            Ok(this)
        } else {
            Err(Error::InvalidType)
        }
    }
}

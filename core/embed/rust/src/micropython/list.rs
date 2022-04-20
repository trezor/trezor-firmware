use core::convert::TryFrom;
use core::ptr;

use crate::error::Error;

use super::{ffi, gc::Gc, obj::Obj, runtime::catch_exception};

pub type List = ffi::mp_obj_list_t;

impl List {
    pub fn alloc(values: &[Obj]) -> Result<Gc<Self>, Error> {
        // SAFETY: Although `values` are copied into the new list and not mutated,
        // `mp_obj_new_list` is taking them through a mut pointer.
        // EXCEPTION: Will raise if allocation fails.
        catch_exception(|| unsafe {
            let list = ffi::mp_obj_new_list(values.len(), values.as_ptr() as *mut Obj);
            Gc::from_raw(list.as_ptr().cast())
        })
    }

    pub fn with_capacity(capacity: usize) -> Result<Gc<Self>, Error> {
        // EXCEPTION: Will raise if allocation fails.
        catch_exception(|| unsafe {
            let list = ffi::mp_obj_new_list(capacity, ptr::null_mut());
            Gc::from_raw(list.as_ptr().cast())
        })
    }

    pub fn from_iter<T, E>(iter: impl Iterator<Item = T>) -> Result<Gc<List>, Error>
    where
        T: TryInto<Obj, Error = E>,
        Error: From<E>,
    {
        let max_size = iter.size_hint().1.unwrap_or(0);
        let mut gc_list = List::with_capacity(max_size)?;
        let list = unsafe { Gc::as_mut(&mut gc_list) };
        for value in iter {
            list.append(value.try_into()?)?;
        }
        Ok(gc_list)
    }

    pub fn append(&mut self, value: Obj) -> Result<(), Error> {
        unsafe {
            let ptr = self as *mut Self;
            let list = Obj::from_ptr(ptr.cast());
            // EXCEPTION: Will raise if allocation fails.
            catch_exception(|| {
                ffi::mp_obj_list_append(list, value);
            })
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
            Err(Error::TypeError)
        }
    }
}

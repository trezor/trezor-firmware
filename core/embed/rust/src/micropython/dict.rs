use core::convert::TryFrom;

use crate::error::Error;

use super::{ffi, gc::Gc, map::Map, obj::Obj};

/// Insides of the MicroPython `dict` object.
pub type Dict = ffi::mp_obj_dict_t;

impl Dict {
    /// Allocate a new dictionary on the GC heap, empty, but with a capacity of
    /// `capacity` items.
    pub fn alloc_with_capacity(capacity: usize) -> Gc<Self> {
        unsafe {
            // SAFETY: We expect that `ffi::mp_obj_new_dict` either returns a GC-allocated
            // pointer to `ffi::mp_obj_dict_t` or raises (i.e. on allocation failure).
            let ptr = ffi::mp_obj_new_dict(capacity);
            Gc::from_raw(ptr.as_ptr().cast())
        }
    }

    /// Constructs a dictionary definition by taking ownership of given [`Map`].
    pub fn with_map(map: Map) -> Self {
        unsafe {
            Self {
                base: ffi::mp_obj_base_t {
                    type_: &ffi::mp_type_dict,
                },
                map,
            }
        }
    }

    /// Returns a reference to the contained [`Map`].
    pub fn map(&self) -> &Map {
        &self.map
    }

    /// Returns a mutable reference to the contained [`Map`].
    pub fn map_mut(&mut self) -> &mut Map {
        &mut self.map
    }
}

impl From<Gc<Dict>> for Obj {
    fn from(value: Gc<Dict>) -> Self {
        // SAFETY:
        //  - `value` is an object struct with a base and a type.
        //  - `value` is GC-allocated.
        unsafe { Obj::from_ptr(Gc::into_raw(value).cast()) }
    }
}

impl TryFrom<Obj> for Gc<Dict> {
    type Error = Error;

    fn try_from(value: Obj) -> Result<Self, Self::Error> {
        if unsafe { ffi::mp_type_dict.is_type_of(value) } {
            // SAFETY: We assume that if `value` is an object pointer with the correct type,
            // it is managed by MicroPython GC (see `Gc::from_raw` for details).
            let this = unsafe { Gc::from_raw(value.as_ptr().cast()) };
            Ok(this)
        } else {
            Err(Error::InvalidType)
        }
    }
}

// SAFETY: We are in a single-threaded environment.
unsafe impl Sync for Dict {}

use crate::gc::Gc;
use crate::map::Map;
use crate::py_object::HasBaseType;
use crate::runtime::catch_exception;
use crate::typ::Type;
use crate::{Error, ffi};

/// Insides of the MicroPython `dict` object.
pub type Dict = ffi::mp_obj_dict_t;

impl Dict {
    /// Allocate a new dictionary on the GC heap, empty, but with a capacity of
    /// `capacity` items.
    pub fn alloc_with_capacity(capacity: usize) -> Result<Gc<Self>, Error> {
        catch_exception(|| unsafe {
            // SAFETY: We expect that `ffi::mp_obj_new_dict` either returns a GC-allocated
            // pointer to `ffi::mp_obj_dict_t` or raises.
            // EXCEPTION: Will raise if allocation fails.
            let ptr = ffi::mp_obj_new_dict(capacity);
            Gc::from_raw(ptr.as_ptr().cast())
        })
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

/// SAFETY: dict type is a builtin and therefore has the right layout.
unsafe impl HasBaseType for Dict {
    fn obj_type() -> &'static Type {
        unsafe { &ffi::mp_type_dict }
    }
}

// SAFETY: We are in a single-threaded environment.
unsafe impl Sync for Dict {}

use super::{
    ffi,
    obj::{Obj, ObjBase},
};

pub type Type = ffi::mp_obj_type_t;

impl Type {
    pub fn is_type_of(&'static self, obj: Obj) -> bool {
        if obj.is_ptr() {
            // SAFETY: If `obj` is a pointer, it should always point to an object having
            // `ObjBase` as the first field, making this cast safe.
            unsafe {
                let base = obj.as_ptr() as *const ObjBase;
                (*base).type_ == self
            }
        } else {
            false
        }
    }

    pub fn to_base(&'static self) -> ObjBase {
        ObjBase { type_: self }
    }
}

// SAFETY: We are in a single-threaded environment.
unsafe impl Sync for Type {}

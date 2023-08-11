use super::{
    ffi,
    obj::{Obj, ObjBase},
};

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

    #[cfg(feature = "debug")]
    pub fn name(&self) -> &'static str {
        use super::qstr::Qstr;

        Qstr::from(self.name).as_str()
    }
}

// SAFETY: We are in a single-threaded environment.
unsafe impl Sync for Type {}

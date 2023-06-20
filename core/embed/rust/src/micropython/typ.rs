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

    #[cfg(feature = "debug")]
    pub fn name(&self) -> &'static str {
        use super::qstr::Qstr;

        Qstr::from(self.name).as_str()
    }
}

// SAFETY: We are in a single-threaded environment.
unsafe impl Sync for Type {}

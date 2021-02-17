use core::ptr;

use super::{
    dict::Dict,
    ffi,
    obj::{Obj, ObjBase},
    qstr::Qstr,
};

pub type Type = ffi::mp_obj_type_t;

pub type MakeNewFn =
    unsafe extern "C" fn(type_: *const Type, n_args: usize, n_kw: usize, args: *const Obj) -> Obj;

impl Type {
    pub fn new() -> Self {
        unsafe {
            Self {
                base: ffi::mp_obj_base_t {
                    type_: &ffi::mp_type_type,
                },
                flags: 0,
                name: 0,
                print: None,
                make_new: None,
                call: None,
                unary_op: None,
                binary_op: None,
                attr: None,
                subscr: None,
                getiter: None,
                iternext: None,
                buffer_p: ffi::mp_buffer_p_t { get_buffer: None },
                protocol: ptr::null(),
                parent: ptr::null(),
                locals_dict: ptr::null_mut(),
            }
        }
    }

    pub fn with_name(mut self, name: Qstr) -> Self {
        self.name = name.to_u16();
        self
    }

    pub fn with_make_new(mut self, make_new: MakeNewFn) -> Self {
        self.make_new = Some(make_new);
        self
    }

    pub fn with_locals(mut self, locals: &'static Dict) -> Self {
        // TODO: This is safe only if we pass in `Dict` with fixed `Map` (created by
        // `Map::fixed()`), because only then will Micropython treat `locals_dict` as
        // immutable, and make the mutable cast safe. Encode this in the type system.
        let locals = locals as *const Dict as *mut Dict;
        self.locals_dict = locals;
        self
    }

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

    pub fn in_base(&'static self) -> ObjBase {
        ObjBase { type_: self }
    }
}

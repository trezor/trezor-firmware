use super::{
    ffi,
    obj::{Obj, ObjBase},
};

/// Number of type "slots" that `obj_type!`/`Type::new` can populate.
///
/// Since MicroPython v1.20 `mp_obj_type_t` stores its method pointers in a
/// trailing `slots[]` array indexed by the `slot_index_*` header fields
/// (1-based, 0 = absent). We only ever need four of them: `make_new`, `call`,
/// `attr` and `locals_dict`. We give each a fixed position in the array;
/// MicroPython only ever dereferences `slots[slot_index_x - 1]`, so a fixed
/// (non-dense) layout with unused null entries is correct.
const TYPE_SLOTS: usize = 4;

const SLOT_MAKE_NEW: usize = 0;
const SLOT_CALL: usize = 1;
const SLOT_ATTR: usize = 2;
const SLOT_LOCALS_DICT: usize = 3;

/// A statically-allocated MicroPython type object.
///
/// Layout-compatible with `mp_obj_type_t` followed by its `slots[]` flexible
/// array member, so `&Type` can be handed to MicroPython as a
/// `*const mp_obj_type_t`.
#[repr(C)]
pub struct Type {
    base: ffi::mp_obj_type_t,
    slots: [*const cty::c_void; TYPE_SLOTS],
}

impl Type {
    /// Build a type object from its (optional) method pointers.
    ///
    /// `make_new`, `call` and `attr` are `Option`s of the matching MicroPython
    /// function-pointer types; `locals_dict` is null when absent. This is the
    /// Rust equivalent of the C `MP_DEFINE_CONST_OBJ_TYPE` macro.
    pub const fn new(
        name: u16,
        base: *const ffi::mp_obj_type_t,
        make_new: ffi::mp_make_new_fun_t,
        call: ffi::mp_call_fun_t,
        attr: ffi::mp_attr_fun_t,
        locals_dict: *mut ffi::mp_obj_dict_t,
    ) -> Self {
        // Erase the (same-sized) function/data pointers to `void *` for storage
        // in the slots array. `None` transmutes to a null pointer.
        // SAFETY: each source type is a single pointer of the same size as
        // `*const c_void`.
        let make_new_slot: *const cty::c_void = unsafe { core::mem::transmute(make_new) };
        let call_slot: *const cty::c_void = unsafe { core::mem::transmute(call) };
        let attr_slot: *const cty::c_void = unsafe { core::mem::transmute(attr) };
        let locals_slot: *const cty::c_void = locals_dict as *const cty::c_void;

        let mut slots: [*const cty::c_void; TYPE_SLOTS] = [core::ptr::null(); TYPE_SLOTS];
        slots[SLOT_MAKE_NEW] = make_new_slot;
        slots[SLOT_CALL] = call_slot;
        slots[SLOT_ATTR] = attr_slot;
        slots[SLOT_LOCALS_DICT] = locals_slot;

        // slot_index is 1-based; 0 means the slot is absent.
        const fn slot_index(present: bool, pos: usize) -> u8 {
            if present {
                (pos + 1) as u8
            } else {
                0
            }
        }

        Type {
            base: ffi::mp_obj_type_t {
                base: ffi::mp_obj_base_t { type_: base },
                flags: 0,
                name,
                slot_index_make_new: slot_index(!make_new_slot.is_null(), SLOT_MAKE_NEW),
                slot_index_print: 0,
                slot_index_call: slot_index(!call_slot.is_null(), SLOT_CALL),
                slot_index_unary_op: 0,
                slot_index_binary_op: 0,
                slot_index_attr: slot_index(!attr_slot.is_null(), SLOT_ATTR),
                slot_index_subscr: 0,
                slot_index_iter: 0,
                slot_index_buffer: 0,
                slot_index_protocol: 0,
                slot_index_parent: 0,
                slot_index_locals_dict: slot_index(!locals_slot.is_null(), SLOT_LOCALS_DICT),
                slots: ffi::__IncompleteArrayField::new(),
            },
            slots,
        }
    }

    /// Pointer to the underlying `mp_obj_type_t` header.
    pub const fn as_mp_type(&'static self) -> *const ffi::mp_obj_type_t {
        &self.base
    }

    pub fn is_type_of(&'static self, obj: Obj) -> bool {
        match obj.type_() {
            Some(type_) => core::ptr::eq(type_, &self.base),
            None => false,
        }
    }

    pub const fn as_base(&'static self) -> ObjBase {
        ObjBase { type_: &self.base }
    }

    pub const fn as_obj(&'static self) -> Obj {
        // SAFETY:
        //  - We are an object struct with a base and a type.
        //  - 'static lifetime holds us in place.
        //  - MicroPython is smart enough not to mutate `mp_obj_type_t` objects.
        unsafe { Obj::from_ptr(&self.base as *const _ as *mut _) }
    }

    #[cfg(feature = "debug")]
    pub fn name(&self) -> &'static str {
        use super::qstr::Qstr;

        Qstr::from(self.base.name).as_str()
    }
}

// SAFETY: We are in a single-threaded environment.
unsafe impl Sync for Type {}

/// Test whether an object is an instance of a bare `mp_obj_type_t`, e.g. one of
/// the built-in `ffi::mp_type_*` statics (which are not wrapped in [`Type`]).
pub trait IsTypeOf {
    fn is_type_of(&self, obj: Obj) -> bool;
}

impl IsTypeOf for ffi::mp_obj_type_t {
    fn is_type_of(&self, obj: Obj) -> bool {
        match obj.type_() {
            Some(type_) => core::ptr::eq(type_, self),
            None => false,
        }
    }
}

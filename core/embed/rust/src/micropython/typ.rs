use core::ops::Deref;

use super::ffi;
use super::obj::{Obj, ObjBase};
use super::qstr::Qstr;

pub type Type = ffi::mp_obj_type_t;

/// Empty type struct, representing a type with no slots.
///
/// Transparently wraps the underlying `mp_obj_empty_type_t` struct,
/// so that we can gate slot values behind unsafe setters.
#[repr(transparent)]
#[derive(Debug)]
pub struct EmptyType(ffi::mp_obj_empty_type_t);

pub const TYPE_BASE: &Type = unsafe { &ffi::mp_type_type };

macro_rules! slot_setter {
    ($name:ident) => {
        /// Set the value of the `$name` slot.
        ///
        /// # Safety
        ///
        /// Caller must ensure that `value - 1` is a valid index within the
        /// owning struct's slot array.
        ///
        /// Example:
        /// ```ignore
        ///
        /// struct MyType {
        ///     head: EmptyType,
        ///     make_new: *const cty::c_void,
        /// }
        ///
        /// let my_type = MyType {
        ///     head: unsafe {
        ///         EmptyType::new(Qstr::MP_QSTR_MyType)
        ///             // CORRECT:
        ///             .slot_index_make_new(1)  // points to slot 0
        ///             // INCORRECT:
        ///             // .slot_index_print(2)    // points to nonexistent slot 1
        ///     },
        ///     make_new: ffi::mp_obj_exception_make_new as *const _,
        /// };
        /// ```
        pub const unsafe fn $name(self, value: u8) -> Self {
            Self(ffi::mp_obj_empty_type_t {
                $name: value,
                ..self.0
            })
        }
    };
}

impl EmptyType {
    /// Construct an empty type with all slots zeroed.
    ///
    /// This is useful as a first item in a `repr(C)` struct
    /// extending to a custom number of slots.
    pub const fn new(name: Qstr) -> Self {
        Self(ffi::mp_obj_empty_type_t {
            base: TYPE_BASE.as_base(),
            flags: 0,
            name: name.to_u16(),
            slot_index_make_new: 0,
            slot_index_print: 0,
            slot_index_call: 0,
            slot_index_unary_op: 0,
            slot_index_binary_op: 0,
            slot_index_attr: 0,
            slot_index_subscr: 0,
            slot_index_iter: 0,
            slot_index_buffer: 0,
            slot_index_protocol: 0,
            slot_index_parent: 0,
            slot_index_locals_dict: 0,
        })
    }

    pub const fn as_type(&self) -> &Type {
        // SAFETY: `EmptyType` is repr(transparent) around `mp_obj_empty_type_t`,
        // which is safe to cast to `Type`.
        unsafe { core::mem::transmute(self) }
    }

    slot_setter!(slot_index_make_new);
    slot_setter!(slot_index_print);
    slot_setter!(slot_index_call);
    slot_setter!(slot_index_unary_op);
    slot_setter!(slot_index_binary_op);
    slot_setter!(slot_index_attr);
    slot_setter!(slot_index_subscr);
    slot_setter!(slot_index_iter);
    slot_setter!(slot_index_buffer);
    slot_setter!(slot_index_protocol);
    slot_setter!(slot_index_parent);
    slot_setter!(slot_index_locals_dict);
}

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

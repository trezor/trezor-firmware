#![allow(non_upper_case_globals)]

use super::{ffi, obj::Obj, qstr::Qstr, typ::Type};

pub const AttributeError: &Type = unsafe { &ffi::mp_type_AttributeError };
pub const EOFError: &Type = unsafe { &ffi::mp_type_EOFError };
pub const Exception: &Type = unsafe { &ffi::mp_type_Exception };
pub const IndexError: &Type = unsafe { &ffi::mp_type_IndexError };
pub const KeyError: &Type = unsafe { &ffi::mp_type_KeyError };
pub const MemoryError: &Type = unsafe { &ffi::mp_type_MemoryError };
pub const NotImplementedError: &Type = unsafe { &ffi::mp_type_NotImplementedError };
pub const OverflowError: &Type = unsafe { &ffi::mp_type_OverflowError };
pub const RuntimeError: &Type = unsafe { &ffi::mp_type_RuntimeError };
pub const TypeError: &Type = unsafe { &ffi::mp_type_TypeError };
pub const ValueError: &Type = unsafe { &ffi::mp_type_ValueError };

pub const fn define_exception(name: Qstr, parent: &Type) -> Type {
    obj_type! {
        name: name,
        make_new_fn: ffi::mp_obj_exception_make_new,
        attr_fn: ffi::mp_obj_exception_attr,
        print_fn: ffi::mp_obj_exception_print,
        parent: parent,
    }
}

/// Create an exception instance. The result of this
/// call should only be used to immediately raise the exception, because the
/// object is not guaranteed to remain intact. MicroPython might reuse the
/// same space for creating a different exception.
///
/// SAFETY: `exc_type` must be a reference to a valid exception type, otherwise
///         micropython might abort.
pub unsafe fn new_exception(exc_type: &'static Type) -> Obj {
    // SAFETY: First argument is a reference to a valid exception type per
    // precondition. EXCEPTION: Sensibly, `new_exception_*` does not raise.
    unsafe { ffi::mp_obj_new_exception(exc_type) }
}

/// Create an exception instance. The result of this
/// call should only be used to immediately raise the exception, because the
/// object is not guaranteed to remain intact. MicroPython might reuse the
/// same space for creating a different exception.
///
/// SAFETY: `exc_type` must be a reference to a valid exception type, otherwise
///         micropython might abort.
pub unsafe fn new_exception_args(exc_type: &'static Type, args: &[Obj]) -> Obj {
    // SAFETY: First argument is a reference to a valid exception type per
    // precondition. EXCEPTION: Sensibly, `new_exception_*` does not raise.
    unsafe { ffi::mp_obj_new_exception_args(exc_type, args.len(), args.as_ptr()) }
}

/// Create an exception instance. The result of this
/// call should only be used to immediately raise the exception, because the
/// object is not guaranteed to remain intact. MicroPython might reuse the
/// same space for creating a different exception.
///
/// SAFETY: `exc_type` must be a reference to a valid exception type, otherwise
///         micropython might abort.
pub unsafe fn new_exception_arg_from(exc_type: &'static Type, arg: impl TryInto<Obj>) -> Obj {
    match arg.try_into() {
        Ok(obj) => unsafe { new_exception_args(exc_type, &[obj]) },
        _ => unsafe { new_exception(exc_type) },
    }
}

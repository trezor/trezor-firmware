#![allow(non_upper_case_globals)]

use super::ffi;
use super::gc::Gc;
use super::obj::Obj;
use super::qstr::Qstr;
use super::tuple::Tuple;
use super::typ::{EmptyType, Type};

/// Exception type.
///
/// Constructed manually from `MP_DEFINE_EXCEPTION` macro:
///
/// ```c
/// #define MP_DEFINE_EXCEPTION(exc_name, base_name) \
///     MP_DEFINE_CONST_OBJ_TYPE(mp_type_##exc_name, MP_QSTR_##exc_name, MP_TYPE_FLAG_NONE, \
///     make_new, mp_obj_exception_make_new, \
///     print, mp_obj_exception_print, \
///     attr, mp_obj_exception_attr, \
///     parent, &mp_type_##base_name \
///     );
/// ```
///
/// This results in a type object with exactly 4 slots.
///
/// # Safety
///
/// Relies on implementation details of MicroPython's exceptions. Generally
/// sound for as long as layout of Type is not changed, but if MicroPython
/// changes the way it recognizes exception types, this might break.
#[derive(Debug)]
#[repr(C)]
pub struct ExceptionType {
    head: EmptyType,
    make_new_slot: *const cty::c_void,
    print_slot: *const cty::c_void,
    attr_slot: *const cty::c_void,
    parent_slot: *const cty::c_void,
}

// SAFETY: ExceptionTypes are always immutable
unsafe impl Sync for ExceptionType {}
unsafe impl Send for ExceptionType {}

impl ExceptionType {
    /// Construct a new exception type as a child of an existing exception type.
    pub const fn new(parent: &'static ExceptionType, name: Qstr) -> Self {
        Self {
            head: unsafe {
                // SAFETY: we have four slots so maximum slot_index 4 is valid
                EmptyType::new(name)
                    .slot_index_make_new(1)
                    .slot_index_print(2)
                    .slot_index_attr(3)
                    .slot_index_parent(4)
            },
            make_new_slot: ffi::mp_obj_exception_make_new as *const _,
            print_slot: ffi::mp_obj_exception_print as *const _,
            attr_slot: ffi::mp_obj_exception_attr as *const _,
            parent_slot: parent as *const _ as _,
        }
    }

    /// Convert the exception type into a regular type.
    pub const fn as_type(&self) -> &Type {
        self.head.as_type()
    }

    /// Check if the exception type is the type of an object.
    pub fn is_type_of(&'static self, other: Obj) -> bool {
        self.as_type().is_type_of(other)
    }
}

/// Builtin exception types
///
/// Collected into a sub-module to avoid name collision of builtin::Exception
/// type with Exception struct.
pub mod builtin {
    use super::ExceptionType;

    /// Wrap a builtin exception type in ExceptionType.
    ///
    /// When `mp_type_SomeError` is created via bindgen, its type is set to
    /// `Type`. The size of `Type` is equal to `EmptyType` -- its last item is
    /// an incomplete array. Rust's static time CTFE disallows us to cast a Type
    /// instance into the larger `ExceptionType`, despite, at run-time, the size
    /// being correct.
    ///
    /// So instead we explicitly import the extern type already declared as
    /// `ExceptionType`, and make a pub reference to it.
    ///
    /// Drawback: if we do it wrong, and import a type that (a) does not
    /// actually match ExceptionType layout, or (b) does not exist, the
    /// problem will be invisible.
    macro_rules! wrap_builtin {
        ($name:ident, $type:ident) => {
            unsafe extern "C" {
                static $type: ExceptionType;
            }
            // SAFETY: provided type must be an exception type.
            pub static $name: &ExceptionType = unsafe { &$type };
        };
    }

    wrap_builtin!(AttributeError, mp_type_AttributeError);
    wrap_builtin!(EOFError, mp_type_EOFError);
    wrap_builtin!(Exception, mp_type_Exception);
    wrap_builtin!(IndexError, mp_type_IndexError);
    wrap_builtin!(KeyError, mp_type_KeyError);
    wrap_builtin!(MemoryError, mp_type_MemoryError);
    wrap_builtin!(NotImplementedError, mp_type_NotImplementedError);
    wrap_builtin!(OverflowError, mp_type_OverflowError);
    wrap_builtin!(RuntimeError, mp_type_RuntimeError);
    wrap_builtin!(TypeError, mp_type_TypeError);
    wrap_builtin!(ValueError, mp_type_ValueError);
}

/// Exception object.
///
/// Represents an unraised exception on Rust side. When creating FFI exceptions
/// via [`ffi::mp_obj_new_exception_args`], the resulting object may be reused
/// by MicroPython for another exception. By keeping the arguments explicitly
/// without constructing the exception, we avoid the problem.
///
/// The actual exception object is then constructed via [`Exception::into_obj`].
///
/// # Safety
///
/// Should not derive Copy / Clone: the object holds an opaque `traceback_data`
/// pointer, which is very likely not a good idea to wildly copy around.
#[derive(Debug)]
pub struct Exception {
    type_: &'static Type,
    args: Gc<Tuple>,
    traceback_alloc: usize,
    traceback_len: usize,
    traceback_data: *mut usize,
}

impl Exception {
    /// Create a new exception with the given type and arguments.
    ///
    /// Tries to allocate an args tuple from the provided arguments. If
    /// allocation fails, instead of returning an error, an empty tuple is used
    /// (like MicroPython does).
    pub fn new(type_: &'static ExceptionType, args: &[Obj]) -> Self {
        Self {
            type_: type_.as_type(),
            args: Tuple::alloc(args).unwrap_or(Tuple::empty()),
            traceback_alloc: 0,
            traceback_len: 0,
            traceback_data: core::ptr::null_mut(),
        }
    }

    /// Create a new exception with the given type and a single argument.
    ///
    /// Tries to convert the argument into a MicroPython object. If conversion
    /// fails, instead of returning an error, an empty tuple is used (like
    /// MicroPython does).
    pub fn new_with_arg(type_: &'static ExceptionType, arg: impl TryInto<Obj>) -> Self {
        let args: &[Obj] = match arg.try_into() {
            Ok(arg) => &[arg],
            Err(_) => &[],
        };
        Self::new(type_, args)
    }

    /// Convert a custom exception into a MicroPython exception object.
    ///
    /// # Safety
    ///
    /// The result of this call should only be used to immediately raise the
    /// exception, because the object is not guaranteed to remain intact.
    /// MicroPython might reuse the same space for creating a different
    /// exception. See [`new_exception_args`].
    unsafe fn into_obj(self) -> Obj {
        // SAFETY: self.type_ is a valid exception type, per construction
        // EXCEPTION: sensibly, mp_obj_new_exception does not raise.
        let maybe_allocated_exception = unsafe { ffi::mp_obj_new_exception(self.type_) };
        // mp_obj_new_exception always returns a pointer
        ensure!(maybe_allocated_exception.is_ptr(), "mp_obj_new_exception");
        // SAFETY:
        // - if the exception is a pointer, it is a valid exception object.
        // - we only hold the reference during the scope of this function.
        let exception: &mut ffi::mp_obj_exception_t =
            unsafe { &mut *(maybe_allocated_exception.as_ptr() as *mut _) };
        // fill out all arguments and possibly also traceback data
        exception.args = Gc::into_raw(self.args);
        exception.set_traceback_alloc(self.traceback_alloc);
        exception.set_traceback_len(self.traceback_len);
        exception.traceback_data = self.traceback_data;

        // SAFETY: the exception is a valid exception object.
        unsafe { Obj::from_ptr(maybe_allocated_exception.as_ptr()) }
    }

    /// Raise the exception into MicroPython
    ///
    /// # Safety
    ///
    /// Jumps directly out of the context without running any destructors,
    /// finalizers, etc. This is very likely to break a lot of Rust's
    /// assumptions: in particular, _any_ jumping over Rust code is
    /// currently considered undefined. See full discussion at
    /// https://github.com/rust-lang/rfcs/issues/2625
    ///
    /// Should only be called at the boundary which would otherwise return to C.
    pub unsafe fn raise(self) -> ! {
        // SAFETY:
        // - into_obj constructs a valid exception instance (satisfying nlr_jump)
        // - this is immediately raised (satisfying into_obj)
        unsafe { ffi::nlr_jump(self.into_obj().as_ptr()) };
    }
}

fn conversion_failed_exception() -> Exception {
    Exception::new_with_arg(builtin::TypeError, "Caught a non-exception object")
}

impl TryFrom<Obj> for Exception {
    // Notice how, on failure, we _also_ return an exception.
    // (but a different one)
    type Error = Exception;

    fn try_from(obj: Obj) -> Result<Self, Self::Error> {
        let Some(exc_type) = obj.type_() else {
            // not a MPy object at all
            return Err(conversion_failed_exception());
        };
        // exceptions must have a make_new slot
        if exc_type.slot_index_make_new == 0 {
            return Err(conversion_failed_exception());
        }
        // SAFETY: the slots slice must be long enough to fit the make_new slot
        let slots = unsafe {
            exc_type
                .slots
                .as_slice(exc_type.slot_index_make_new as usize)
        };
        // slot indices are 1-based
        let make_new = slots[exc_type.slot_index_make_new as usize - 1];

        // same check as objexcept.c does for making sure it is an exception type
        if make_new != ffi::mp_obj_exception_make_new as *const _ {
            // not an exception type
            return Err(conversion_failed_exception());
        }

        // now we can extract the exception type
        // SAFETY:
        // - obj is a valid exception object (per mpy checking rules)
        // - reference does not outlive the scope of this function
        let exception = unsafe { &*(obj.as_ptr() as *const ffi::mp_obj_exception_t) };

        let args = if exception.args.is_null() {
            Tuple::empty()
        } else {
            // SAFETY: exception.args are explicitly a pointer
            // to a tuple object
            unsafe { Gc::from_raw(exception.args.cast()) }
        };

        let new = Self {
            type_: exc_type,
            args,
            traceback_alloc: exception.traceback_alloc(),
            traceback_len: exception.traceback_len(),
            traceback_data: exception.traceback_data,
        };
        Ok(new)
    }
}

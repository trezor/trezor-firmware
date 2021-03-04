use super::{ffi, obj::Obj};

pub type Func = ffi::mp_obj_fun_builtin_fixed_t;

impl Func {
    pub const fn to_obj(&'static self) -> Obj {
        // SAFETY:
        //  - We are an object struct with a base and a type.
        //  - 'static lifetime holds us in place.
        //  - Micropython is smart enough not to mutate builtin function objects.
        unsafe { Obj::from_ptr(self as *const _ as *mut _) }
    }
}

// SAFETY: We are in a single-threaded environment.
unsafe impl Sync for Func {}

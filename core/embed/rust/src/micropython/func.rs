use super::{ffi, obj::Obj};

pub struct Func {
    func: ffi::mp_obj_fun_builtin_fixed_t,
}

pub type ExternFunc1 = unsafe extern "C" fn(x: Obj) -> Obj;
pub type ExternFunc2 = unsafe extern "C" fn(x: Obj, y: Obj) -> Obj;
pub type ExternFunc3 = unsafe extern "C" fn(x: Obj, y: Obj, z: Obj) -> Obj;

impl Func {
    pub fn extern_1(func: ExternFunc1) -> Self {
        unsafe {
            Self {
                func: ffi::mp_obj_fun_builtin_fixed_t {
                    base: ffi::mp_obj_base_t {
                        type_: &ffi::mp_type_fun_builtin_1,
                    },
                    fun: ffi::_mp_obj_fun_builtin_fixed_t__bindgen_ty_1 { _1: Some(func) },
                },
            }
        }
    }

    pub fn extern_2(func: ExternFunc2) -> Self {
        unsafe {
            Self {
                func: ffi::mp_obj_fun_builtin_fixed_t {
                    base: ffi::mp_obj_base_t {
                        type_: &ffi::mp_type_fun_builtin_2,
                    },
                    fun: ffi::_mp_obj_fun_builtin_fixed_t__bindgen_ty_1 { _2: Some(func) },
                },
            }
        }
    }

    pub fn extern_3(func: ExternFunc3) -> Self {
        unsafe {
            Self {
                func: ffi::mp_obj_fun_builtin_fixed_t {
                    base: ffi::mp_obj_base_t {
                        type_: &ffi::mp_type_fun_builtin_3,
                    },
                    fun: ffi::_mp_obj_fun_builtin_fixed_t__bindgen_ty_1 { _3: Some(func) },
                },
            }
        }
    }

    pub fn to_obj(&'static self) -> Obj {
        // SAFETY:
        //  - We are an object struct with a base and a type.
        //  - 'static lifetime holds us in place.
        //  - Micropython is smart enough not to mutate builtin function objects.
        unsafe { Obj::from_ptr(self as *const _ as *mut _) }
    }
}

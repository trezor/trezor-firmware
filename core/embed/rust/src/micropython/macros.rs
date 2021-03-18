macro_rules! obj_fn_1 {
    ($f:expr) => {{
        #[allow(unused_unsafe)]
        unsafe {
            use $crate::micropython::ffi;

            ffi::mp_obj_fun_builtin_fixed_t {
                base: ffi::mp_obj_base_t {
                    type_: &ffi::mp_type_fun_builtin_1,
                },
                fun: ffi::_mp_obj_fun_builtin_fixed_t__bindgen_ty_1 { _1: Some($f) },
            }
        }
    }};
}

macro_rules! obj_fn_2 {
    ($f:expr) => {{
        #[allow(unused_unsafe)]
        unsafe {
            use $crate::micropython::ffi;

            ffi::mp_obj_fun_builtin_fixed_t {
                base: ffi::mp_obj_base_t {
                    type_: &ffi::mp_type_fun_builtin_2,
                },
                fun: ffi::_mp_obj_fun_builtin_fixed_t__bindgen_ty_1 { _2: Some($f) },
            }
        }
    }};
}

macro_rules! obj_fn_3 {
    ($f:expr) => {{
        #[allow(unused_unsafe)]
        unsafe {
            use $crate::micropython::ffi;

            ffi::mp_obj_fun_builtin_fixed_t {
                base: ffi::mp_obj_base_t {
                    type_: &ffi::mp_type_fun_builtin_3,
                },
                fun: ffi::_mp_obj_fun_builtin_fixed_t__bindgen_ty_1 { _3: Some($f) },
            }
        }
    }};
}

/// Construct fixed static const `Map` from `key` => `val` pairs.
macro_rules! obj_map {
    ($($key:expr => $val:expr),*) => ({
        Map::from_fixed_static(&[
            $(
                Map::at($key, $val),
            )*
        ])
    });
    ($($key:expr => $val:expr),* ,) => ({
        obj_map!($($key => $val),*)
    });
}

/// Construct a `Dict` from the backing `Map`. See `obj_map` above.
macro_rules! obj_dict {
    ($map:expr) => {{
        #[allow(unused_unsafe)]
        unsafe {
            use $crate::micropython::ffi;

            ffi::mp_obj_dict_t {
                base: ffi::mp_obj_base_t {
                    type_: &ffi::mp_type_dict,
                },
                map: $map,
            }
        }
    }};
}

macro_rules! obj_type {
    (name: $name:expr,
     $(locals: $locals:expr,)?
     $(attr_fn: $attr_fn:ident,)?
     $(call_fn: $call_fn:ident,)?
    ) => {{
        #[allow(unused_unsafe)]
        unsafe {
            use $crate::micropython::ffi;

            let name = $name.to_u16();

            #[allow(unused_mut)]
            #[allow(unused_assignments)]
            let mut attr: ffi::mp_attr_fun_t = None;
            $(attr = Some($attr_fn);)?

            #[allow(unused_mut)]
            #[allow(unused_assignments)]
            let mut call: ffi::mp_call_fun_t = None;
            $(call = Some($call_fn);)?

            // TODO: This is safe only if we pass in `Dict` with fixed `Map` (created by
            // `Map::fixed()`), because only then will Micropython treat `locals_dict` as
            // immutable, and make the mutable cast safe.
            #[allow(unused_mut)]
            #[allow(unused_assignments)]
            let mut locals_dict = ::core::ptr::null_mut();
            $(locals_dict = $locals as *const _ as *mut _;)?

            ffi::mp_obj_type_t {
                base: ffi::mp_obj_base_t {
                    type_: &ffi::mp_type_type,
                },
                flags: 0,
                name,
                print: None,
                make_new: None,
                call,
                unary_op: None,
                binary_op: None,
                attr,
                subscr: None,
                getiter: None,
                iternext: None,
                buffer_p: ffi::mp_buffer_p_t { get_buffer: None },
                protocol: ::core::ptr::null(),
                parent: ::core::ptr::null(),
                locals_dict,
            }
        }
    }};
}

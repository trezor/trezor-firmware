/// Create an object for an exported function taking 1 arg.
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

/// Create an object for an exported function taking 2 args.
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

/// Create an object for an exported function taking 3 args.
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

/// Create an object for an exported function taking a variable number of args.
macro_rules! obj_fn_var {
    ($min:expr, $max:expr, $f:expr) => {{
        #[allow(unused_unsafe)]
        unsafe {
            use $crate::micropython::ffi;

            ffi::mp_obj_fun_builtin_var_t {
                base: ffi::mp_obj_base_t {
                    type_: &ffi::mp_type_fun_builtin_var,
                },
                sig: ($min << 17u32) | ($max << 1u32) | 0, // min, max, takes_kw
                fun: ffi::_mp_obj_fun_builtin_var_t__bindgen_ty_1 { var: Some($f) },
            }
        }
    }};
}

/// Create an object for an exported function taking key-value args.
macro_rules! obj_fn_kw {
    ($min:expr, $f:expr) => {{
        #[allow(unused_unsafe)]
        unsafe {
            use $crate::micropython::ffi;

            ffi::mp_obj_fun_builtin_var_t {
                base: ffi::mp_obj_base_t {
                    type_: &ffi::mp_type_fun_builtin_var,
                },
                sig: ($min << 17u32) | (0xffff << 1u32) | 1, // min, max, takes_kw
                fun: ffi::_mp_obj_fun_builtin_var_t__bindgen_ty_1 { kw: Some($f) },
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

/// Compose a `Type` object definition.
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
            // `Map::fixed()`, usually through `obj_map!`), because only then will
            // MicroPython treat `locals_dict` as immutable, and make the mutable cast safe.
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

/// Construct an extmod definition.
macro_rules! obj_module {
    ($($key:expr => $val:expr),*) => ({
        #[allow(unused_unsafe)]
        #[allow(unused_doc_comments)]
        unsafe {
            use $crate::micropython::ffi;

            static DICT: ffi::mp_obj_dict_t = ffi::mp_obj_dict_t {
                base: ffi::mp_obj_base_t {
                    /// SAFETY: Reasonable to assume the pointer stays valid.
                    type_: unsafe { &ffi::mp_type_dict },
                },
                map: Map::from_fixed_static(&[
                    $(
                        Map::at($key, $val),
                    )*
                ])
            };
            ffi::mp_obj_module_t {
                base: ffi::mp_obj_base_t {
                    type_: &ffi::mp_type_module,
                },
                // This is safe only because we are passing in a static dict with fixed `Map`
                // (created by `Map::from_fixed_static()`). Only then will MicroPython treat
                // `globals` as immutable, making the mutable cast safe.
                globals: &DICT as *const _ as *mut _,
            }
    }});
    ($($key:expr => $val:expr),* ,) => ({
        obj_module!($($key => $val),*)
    });
}

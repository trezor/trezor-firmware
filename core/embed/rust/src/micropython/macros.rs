/// Create an object for an exported function taking no arguments.
macro_rules! obj_fn_0 {
    ($f:expr) => {{
        #[allow(unused_unsafe)]
        unsafe {
            use $crate::micropython::ffi;

            ffi::mp_obj_fun_builtin_fixed_t {
                base: ffi::mp_obj_base_t {
                    type_: &ffi::mp_type_fun_builtin_0,
                },
                fun: ffi::_mp_obj_fun_builtin_fixed_t__bindgen_ty_1 { _0: Some($f) },
            }
        }
    }};
}

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
     $(make_new_fn: $make_new_fn:path,)?
     $(attr_fn: $attr_fn:path,)?
     $(call_fn: $call_fn:path,)?
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

            #[allow(unused_mut)]
            #[allow(unused_assignments)]
            let mut make_new: ffi::mp_make_new_fun_t = None;
            $(make_new = Some($make_new_fn);)?

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
                make_new,
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

macro_rules! attr_tuple {
    (@append
        fields: [$($fields:expr,)*],
        values: [$($values:expr,)*],
        rest: {
            $field:expr => $val:expr,
            $($rest:tt)*
        }
    ) => {
        attr_tuple! {
            @append
            fields: [$($fields,)* $field,],
            values: [$($values,)* $val,],
            rest: {$($rest)*}
        }
    };
    (@append
        fields: [$($fields:expr,)*],
        values: [$($values:expr,)*],
        rest: {}
    ) => {
        $crate::micropython::util::new_attrtuple(&[$($fields,)*], &[$($values,)*])
    };
    // version without trailing comma
    ($($key:expr => $val:expr),*) => ({
        attr_tuple!(@append fields: [], values: [], rest: { $($key => $val,)* })
    });
    // version with trailing comma
    ($($key:expr => $val:expr,)*) => ({
        attr_tuple!(@append fields: [], values: [], rest: { $($key => $val,)* })
    });
}

/// Print arbitrary amounts of slices into a terminal.
/// Does not include a newline at the end.
/// Does not do anything when not in debugging mode.
#[allow(unused_macros)] // Should be used only for debugging purposes
macro_rules! print {
    ($($string:expr),+) => {
        #[cfg(feature = "debug")]
        {
            $(crate::micropython::print::print($string);)+
        }
    }
}

/// Print arbitrary amounts of slices into a terminal.
/// Includes a newline at the end.
/// Does not do anything when not in debugging mode.
#[allow(unused_macros)] // Should be used only for debugging purposes
macro_rules! println {
    ($($string:expr),+) => {
        // Just delegating to print! and adding a newline
        print!($($string),+, "\n");
    }
}

macro_rules! _obj_fn_make_fixed {
    ($type:ident, $member:ident, $f:expr) => {{
        #[allow(unused_unsafe)]
        unsafe {
            use $crate::micropython::ffi;

            ffi::mp_obj_fun_builtin_fixed_t {
                base: ffi::mp_obj_base_t {
                    type_: &$crate::micropython::ffi::$type,
                },
                fun: ffi::_mp_obj_fun_builtin_fixed_t__bindgen_ty_1 { $member: Some($f) },
            }
        }
    }};
}

/// Create an object for an exported function taking no arguments.
macro_rules! obj_fn_0 {
    ($f:expr) => {
        crate::micropython::macros::_obj_fn_make_fixed!(mp_type_fun_builtin_0, _0, $f)
    };
}

/// Create an object for an exported function taking 1 arg.
macro_rules! obj_fn_1 {
    ($f:expr) => {
        crate::micropython::macros::_obj_fn_make_fixed!(mp_type_fun_builtin_1, _1, $f)
    };
}

/// Create an object for an exported function taking 2 args.
macro_rules! obj_fn_2 {
    ($f:expr) => {
        crate::micropython::macros::_obj_fn_make_fixed!(mp_type_fun_builtin_2, _2, $f)
    };
}

/// Create an object for an exported function taking 3 args.
macro_rules! obj_fn_3 {
    ($f:expr) => {
        crate::micropython::macros::_obj_fn_make_fixed!(mp_type_fun_builtin_3, _3, $f)
    };
}

macro_rules! _obj_fn_make_var {
    ($min:expr, $max:expr, takes_kw: $takes_kw:expr, $var_or_kw:ident: $f:expr) => {{
        #[allow(unused_unsafe)]
        unsafe {
            use $crate::micropython::ffi;

            ffi::mp_obj_fun_builtin_var_t {
                base: ffi::mp_obj_base_t {
                    type_: &ffi::mp_type_fun_builtin_var,
                },
                sig: ($min << 17u32) | ($max << 1u32) | $takes_kw,
                fun: ffi::_mp_obj_fun_builtin_var_t__bindgen_ty_1 {
                    $var_or_kw: Some($f),
                },
            }
        }
    }};
}

/// Create an object for an exported function taking a variable number of args
/// between min and max
macro_rules! obj_fn_var {
    ($min:expr, $max:expr, $f:expr) => {
        crate::micropython::macros::_obj_fn_make_var!($min, $max, takes_kw:0, var:$f)
    };
}

/// Create an object for an exported function taking key-value args.
macro_rules! obj_fn_kw {
    ($min:expr, $f:expr) => {
        crate::micropython::macros::_obj_fn_make_var!($min, 0xffff, takes_kw:1, kw:$f)
    };
}

/// Construct fixed static const `Map` from `key` => `val` pairs.
macro_rules! obj_map {
    ($($key:expr => $val:expr),*) => ({
        $crate::micropython::map::Map::from_fixed_static(&[
            $(
                $crate::micropython::map::Map::at($key, $val),
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
     $(base: $base:expr,)?
     $(locals: $locals:expr,)?
     $(make_new_fn: $make_new_fn:path,)?
     $(attr_fn: $attr_fn:path,)?
     $(call_fn: $call_fn:path,)?
     $(print_fn: $print_fn:path,)?
     $(parent: $parent:path,)?
    ) => {{
        use $crate::micropython::ffi;

        let name = $name.to_u16();

        #[allow(unused_mut)]
        #[allow(unused_assignments)]
        // SAFETY: micropython ffi
        let mut base_type: &'static ffi::mp_obj_type_t = unsafe { &ffi::mp_type_type };
        $(base_type = &$base;)?

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

        #[allow(unused_mut)]
        #[allow(unused_assignments)]
        let mut print: ffi::mp_print_fun_t = None;
        $(print = Some($print_fn);)?

        #[allow(unused_mut)]
        #[allow(unused_assignments)]
        let mut parent: Option<&ffi::mp_obj_type_t> = None;
        $(parent = Some($parent);)?

        // TODO: This is safe only if we pass in `Dict` with fixed `Map` (created by
        // `Map::fixed()`, usually through `obj_map!`), because only then will
        // MicroPython treat `locals_dict` as immutable, and make the mutable cast safe.
        #[allow(unused_mut)]
        #[allow(unused_assignments)]
        let mut locals_dict: Option<&ffi::mp_obj_dict_t> = None;
        $(locals_dict = Some($locals);)?

        const fn slot<T>(val: &Option<T>, num: u8) -> u8 {
            if val.is_some() { num } else { 0 }
        }

        ffi::mp_obj_full_type_t {
            base: ffi::mp_obj_base_t {
                type_: base_type,
            },
            flags: ffi::MP_TYPE_FLAG_NONE as u16,
            name,

            slot_index_make_new: slot(&make_new, 1),
            slot_index_print: slot(&print, 2),
            slot_index_call: slot(&call, 3),
            slot_index_unary_op: 0,
            slot_index_binary_op: 0,
            slot_index_attr: slot(&attr, 4),
            slot_index_subscr: 0,
            slot_index_iter: 0,
            slot_index_buffer: 0,
            slot_index_protocol: 0,
            slot_index_parent: slot(&parent, 5),
            slot_index_locals_dict: slot(&locals_dict, 6),

            slots: [
                obj_type!(@cast_fn make_new),
                obj_type!(@cast_fn print),
                obj_type!(@cast_fn call),
                obj_type!(@cast_fn attr),
                obj_type!(@cast_ref parent),
                obj_type!(@cast_ref locals_dict),
                ::core::ptr::null(),
                ::core::ptr::null(),
                ::core::ptr::null(),
                ::core::ptr::null(),
                ::core::ptr::null(),
            ],
        }
    }};
    // Option<unsafe extern "C" fn(...)> => *const cty::c_void
    (@cast_fn $e:expr) => {
        match $e {
            None => ::core::ptr::null(),
            Some(x) => x as *const cty::c_void,
        }
    };
    // Option<&T> => *const cty::c_void
    (@cast_ref $e:expr) => {
        match $e {
            None => ::core::ptr::null(),
            Some(x) => x as *const _ as *const cty::c_void,
        }
    };
}

/// Construct an upymod definition.
macro_rules! obj_module {
    ($($key:expr => $val:expr),*) => ({
        #[allow(unused_unsafe)]
        #[allow(unused_doc_comments)]
        unsafe {
            use $crate::micropython::{ffi, map::Map};

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

// required because they are used in expansion of macros below
pub(crate) use _obj_fn_make_fixed;
pub(crate) use _obj_fn_make_var;
pub(crate) use attr_tuple;
pub(crate) use obj_dict;
pub(crate) use obj_fn_0;
pub(crate) use obj_fn_1;
pub(crate) use obj_fn_2;
pub(crate) use obj_fn_3;
pub(crate) use obj_fn_kw;
pub(crate) use obj_fn_var;
pub(crate) use obj_map;
pub(crate) use obj_module;
pub(crate) use obj_type;

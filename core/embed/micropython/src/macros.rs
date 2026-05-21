// Copyright (c) 2026 Trezor Company s.r.o.
//
// Permission is hereby granted, free of charge, to any person obtaining a copy
// of this software and associated documentation files (the "Software"), to deal
// in the Software without restriction, including without limitation the rights
// to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
// copies of the Software, and to permit persons to whom the Software is
// furnished to do so, subject to the following conditions:
//
// The above copyright notice and this permission notice shall be included in
// all copies or substantial portions of the Software.
//
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
// AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
// LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
// OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
// SOFTWARE.

#[macro_export]
macro_rules! _obj_fn_make_fixed {
    ($type:ident, $member:ident, $f:expr) => {{
        #[allow(unused_unsafe)]
        unsafe {
            use $crate::ffi;

            ffi::mp_obj_fun_builtin_fixed_t {
                base: ffi::mp_obj_base_t {
                    type_: &$crate::ffi::$type,
                },
                fun: ffi::_mp_obj_fun_builtin_fixed_t__bindgen_ty_1 { $member: Some($f) },
            }
        }
    }};
}

/// Create an object for an exported function taking no arguments.
#[macro_export]
macro_rules! obj_fn_0 {
    ($f:expr) => {
        $crate::macros::_obj_fn_make_fixed!(mp_type_fun_builtin_0, _0, $f)
    };
}

/// Create an object for an exported function taking 1 arg.
#[macro_export]
macro_rules! obj_fn_1 {
    ($f:expr) => {
        $crate::macros::_obj_fn_make_fixed!(mp_type_fun_builtin_1, _1, $f)
    };
}

/// Create an object for an exported function taking 2 args.
#[macro_export]
macro_rules! obj_fn_2 {
    ($f:expr) => {
        $crate::macros::_obj_fn_make_fixed!(mp_type_fun_builtin_2, _2, $f)
    };
}

/// Create an object for an exported function taking 3 args.
#[macro_export]
macro_rules! obj_fn_3 {
    ($f:expr) => {
        $crate::macros::_obj_fn_make_fixed!(mp_type_fun_builtin_3, _3, $f)
    };
}

#[macro_export]
macro_rules! _obj_fn_make_var {
    ($min:expr, $max:expr, takes_kw: $takes_kw:expr, $var_or_kw:ident: $f:expr) => {{
        #[allow(unused_unsafe)]
        unsafe {
            use $crate::ffi;

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
#[macro_export]
macro_rules! obj_fn_var {
    ($min:expr, $max:expr, $f:expr) => {
        $crate::macros::_obj_fn_make_var!($min, $max, takes_kw:0, var:$f)
    };
}

/// Create an object for an exported function taking key-value args.
#[macro_export]
macro_rules! obj_fn_kw {
    ($min:expr, $f:expr) => {
        $crate::macros::_obj_fn_make_var!($min, 0xffff, takes_kw:1, kw:$f)
    };
}

/// Construct fixed static const `Map` from `key` => `val` pairs.
#[macro_export]
macro_rules! obj_map {
    ($($key:expr => $val:expr),*) => ({
        $crate::map::Map::from_fixed_static(&[
            $(
                $crate::map::Map::at($crate::qstr::Attribute::from_qstr_value($key), $val),
            )*
        ])
    });
    ($($key:expr => $val:expr),* ,) => ({
        obj_map!($($key => $val),*)
    });
}

/// Construct a `Dict` from the backing `Map`. See `obj_map` above.
#[macro_export]
macro_rules! obj_dict {
    ($map:expr) => {{
        #[allow(unused_unsafe)]
        unsafe {
            use $crate::ffi;

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
#[macro_export]
macro_rules! obj_type {
    (name: $name:expr,
     $(base: $base:expr,)?
     $(locals: $locals:expr,)?
     $(make_new_fn: $make_new_fn:path,)?
     $(attr_fn: $attr_fn:path,)?
     $(call_fn: $call_fn:path,)?
    ) => {{
        #[allow(unused_unsafe)]
        unsafe {
            use $crate::ffi;

            let name = $crate::qstr::qstr_value_to_u16($name);

            #[allow(unused_mut)]
            #[allow(unused_assignments)]
            let mut base_type: &'static ffi::mp_obj_type_t = &ffi::mp_type_type;
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

            // TODO: This is safe only if we pass in `Dict` with fixed `Map` (created by
            // `Map::fixed()`, usually through `obj_map!`), because only then will
            // MicroPython treat `locals_dict` as immutable, and make the mutable cast safe.
            #[allow(unused_mut)]
            #[allow(unused_assignments)]
            let mut locals_dict = ::core::ptr::null_mut();
            $(locals_dict = $locals as *const _ as *mut _;)?

            ffi::mp_obj_type_t {
                base: ffi::mp_obj_base_t {
                    type_: base_type,
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

/// Construct an upymod definition.
#[macro_export]
macro_rules! obj_module {
    ($($key:expr => $val:expr),*) => ({
        #[allow(unused_unsafe)]
        #[allow(unused_doc_comments)]
        unsafe {
            use $crate::{ffi, map::Map, qstr::Attribute};

            static DICT: ffi::mp_obj_dict_t = ffi::mp_obj_dict_t {
                base: ffi::mp_obj_base_t {
                    /// SAFETY: Reasonable to assume the pointer stays valid.
                    type_: unsafe { &ffi::mp_type_dict },
                },
                map: Map::from_fixed_static(&[
                    $(
                        Map::at(Attribute::from_qstr_value($key), $val),
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

#[macro_export]
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
            fields: [$($fields,)* Attribute::from_qstr_value($field),],
            values: [$($values,)* $val,],
            rest: {$($rest)*}
        }
    };
    (@append
        fields: [$($fields:expr,)*],
        values: [$($values:expr,)*],
        rest: {}
    ) => {{
        use $crate::qstr::Attribute;
        static ATTRIBUTES: &[Attribute] = &[$($fields,)*];
        $crate::util::new_attrtuple(ATTRIBUTES, &[$($values,)*])
    }};
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
pub use _obj_fn_make_fixed;
pub use _obj_fn_make_var;

pub use attr_tuple;
pub use obj_dict;
pub use obj_fn_0;
pub use obj_fn_1;
pub use obj_fn_2;
pub use obj_fn_3;
pub use obj_fn_kw;
pub use obj_fn_var;
pub use obj_map;
pub use obj_module;
pub use obj_type;

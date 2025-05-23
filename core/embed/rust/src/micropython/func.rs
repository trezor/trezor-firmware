// Copyright (c) 2025 Trezor Company s.r.o.
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

use super::{ffi, obj::Obj};

pub type Func = ffi::mp_obj_fun_builtin_fixed_t;

impl Func {
    /// Convert a "static const" function to a MicroPython object.
    pub const fn as_obj(&'static self) -> Obj {
        // SAFETY:
        //  - We are an object struct with a base and a type.
        //  - 'static lifetime holds us in place.
        //  - MicroPython is smart enough not to mutate `mp_obj_fun_builtin_fixed_t`
        //    objects.
        unsafe { Obj::from_ptr(self as *const _ as *mut _) }
    }
}

// SAFETY: We are in a single-threaded environment.
unsafe impl Sync for Func {}

pub type FuncVar = ffi::mp_obj_fun_builtin_var_t;

impl FuncVar {
    /// Convert variable argument "static const" function to a MicroPython
    /// object.
    pub const fn as_obj(&'static self) -> Obj {
        // SAFETY:
        //  - We are an object struct with a base and a type.
        //  - 'static lifetime holds us in place.
        //  - MicroPython is smart enough not to mutate `mp_obj_fun_builtin_var_t`
        //    objects.
        unsafe { Obj::from_ptr(self as *const _ as *mut _) }
    }
}

// SAFETY: We are in a single-threaded environment.
unsafe impl Sync for FuncVar {}

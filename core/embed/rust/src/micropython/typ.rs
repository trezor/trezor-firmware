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

use super::{
    ffi,
    obj::{Obj, ObjBase},
};

pub type Type = ffi::mp_obj_type_t;

impl Type {
    pub fn is_type_of(&'static self, obj: Obj) -> bool {
        match obj.type_() {
            Some(type_) => core::ptr::eq(type_, self),
            None => false,
        }
    }

    pub const fn as_base(&'static self) -> ObjBase {
        ObjBase { type_: self }
    }

    pub const fn as_obj(&'static self) -> Obj {
        // SAFETY:
        //  - We are an object struct with a base and a type.
        //  - 'static lifetime holds us in place.
        //  - MicroPython is smart enough not to mutate `mp_obj_type_t` objects.
        unsafe { Obj::from_ptr(self as *const _ as *mut _) }
    }

    #[cfg(feature = "debug")]
    pub fn name(&self) -> &'static str {
        use super::qstr::Qstr;

        Qstr::from(self.name).as_str()
    }
}

// SAFETY: We are in a single-threaded environment.
unsafe impl Sync for Type {}

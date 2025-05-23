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
    obj::{Obj, ObjBase},
    typ::Type,
};

/// Simple MicroPython object type builder.
///
/// This is a struct that can be used to build a MicroPython-exported type which
/// has no data. The caller must generate the type information using the
/// `obj_type!` macro, and use this type to create the corresponding type object
/// visible to MicroPython.
///
/// Example:
/// ```
/// use crate::micropython::{obj::Obj, simple_type::SimpleTypeObj, typ::Type};
///
/// static CONFIRMED_TYPE: Type = obj_type! { name: Qstr::MP_QSTR_CONFIRMED, };
///
/// static CONFIRMED_OBJ: SimpleTypeObj = SimpleTypeObj::new(&CONFIRMED_TYPE);
///
/// let my_type = CONFIRMED_OBJ.as_obj();
/// ```
#[repr(C)]
pub struct SimpleTypeObj {
    base: ObjBase,
}

impl SimpleTypeObj {
    pub const fn new(base: &'static Type) -> Self {
        Self {
            base: base.as_base(),
        }
    }

    /// Convert SimpleType to a MicroPython object.
    pub const fn as_obj(&'static self) -> Obj {
        // SAFETY:
        //  - We are an object struct with a base and a type.
        //  - 'static lifetime holds us in place.
        //  - There's nothing to mutate.
        unsafe { Obj::from_ptr(self as *const _ as *mut _) }
    }
}

// SAFETY: We are in a single-threaded environment.
unsafe impl Sync for SimpleTypeObj {}

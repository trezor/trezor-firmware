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

use crate::gc::Gc;
use crate::map::Map;
use crate::py_object::HasBaseType;
use crate::runtime::catch_exception;
use crate::typ::Type;
use crate::{Error, ffi};

/// Insides of the MicroPython `dict` object.
pub type Dict = ffi::mp_obj_dict_t;

impl Dict {
    /// Allocate a new dictionary on the GC heap, empty, but with a capacity of
    /// `capacity` items.
    pub fn alloc_with_capacity(capacity: usize) -> Result<Gc<Self>, Error> {
        // SAFETY: We expect that `ffi::mp_obj_new_dict` either returns a GC-allocated
        // pointer to `ffi::mp_obj_dict_t` or raises.
        // EXCEPTION: Will raise if allocation fails.
        let ptr = catch_exception!(unsafe { ffi::mp_obj_new_dict } => { capacity })?;
        // SAFETY: `ptr` is a freshly created dict
        Ok(unsafe { Gc::from_raw(ptr.as_ptr().cast()) })
    }

    /// Constructs a dictionary definition by taking ownership of given [`Map`].
    pub fn with_map(map: Map) -> Self {
        unsafe {
            Self {
                base: ffi::mp_obj_base_t {
                    type_: &ffi::mp_type_dict,
                },
                map,
            }
        }
    }

    /// Returns a reference to the contained [`Map`].
    pub fn map(&self) -> &Map {
        &self.map
    }

    /// Returns a mutable reference to the contained [`Map`].
    pub fn map_mut(&mut self) -> &mut Map {
        &mut self.map
    }
}

/// SAFETY: dict type is a builtin and therefore has the right layout.
unsafe impl HasBaseType for Dict {
    fn obj_type() -> &'static Type {
        unsafe { &ffi::mp_type_dict }
    }
}

// SAFETY: We are in a single-threaded environment.
unsafe impl Sync for Dict {}

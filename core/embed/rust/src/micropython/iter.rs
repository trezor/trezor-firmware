use core::ptr;

use crate::error::Error;
use crate::micropython::obj::Obj;

// micropython/py/obj.h mp_obj_base_t
#[repr(C)]
struct ObjBase {
    type_: *const cty::c_void,
}

// micropython/py/obj.h mp_obj_iter_buf_t
#[repr(C)]
struct ObjIterBuf {
    base: ObjBase,
    buf: [Obj; 3],
}

extern "C" {
    // micropython/py/runtime.h
    // Raises if `o` is not iterable and in other cases as well.
    // Returned obj is referencing into `iter_buf`.
    // TODO: Use a fn that doesn't raise on non-iterable object.
    fn mp_getiter(o: Obj, iter_buf: *mut ObjIterBuf) -> Obj;

    // micropython/py/runtime.h
    // Can raise.
    fn mp_iternext(o: Obj) -> Obj;
}

pub struct IterBuf {
    iter_buf: ObjIterBuf,
}

impl IterBuf {
    pub fn new() -> Self {
        Self {
            iter_buf: ObjIterBuf {
                base: ObjBase {
                    type_: ptr::null_mut(),
                },
                buf: [Obj::const_null(), Obj::const_null(), Obj::const_null()],
            },
        }
    }

    fn ptr_mut(&mut self) -> *mut ObjIterBuf {
        &mut self.iter_buf as *mut ObjIterBuf
    }
}

pub struct Iter<'a> {
    iter: Obj,
    iter_buf: &'a mut IterBuf,
    finished: bool,
}

impl<'a> Iter<'a> {
    pub fn try_from_obj_with_buf(o: Obj, iter_buf: &'a mut IterBuf) -> Result<Self, Error> {
        // TODO: Use a fn that doesn't raise on non-iterable object.
        // SAFETY: When passed an `iter_buf`, `mp_getiter` usually does not
        // heap-allocate, but instead returns a view into the passed object. We maintain
        // this invariant by taking a mut ref to `IterBuf` and tying it to the
        // lifetime of returned `Iter`.
        let iter = unsafe { mp_getiter(o, iter_buf.ptr_mut()) };
        Ok(Self {
            iter,
            iter_buf,
            finished: false,
        })
    }
}

impl<'a> Iterator for Iter<'a> {
    type Item = Obj;

    fn next(&mut self) -> Option<Self::Item> {
        if self.finished {
            return None;
        }
        // SAFETY: We assume that `mp_iternext` returns objects without any lifetime
        // invariants, i.e. heap-allocated, unlike `mp_getiter`.
        let item = unsafe { mp_iternext(self.iter) };
        if item == Obj::const_stop_iteration() {
            self.finished = true;
            None
        } else {
            Some(item)
        }
    }
}

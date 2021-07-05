use core::ptr;

use crate::error::Error;
use crate::micropython::obj::Obj;

use super::ffi;

pub struct IterBuf {
    iter_buf: ffi::mp_obj_iter_buf_t,
}

impl IterBuf {
    pub fn new() -> Self {
        Self {
            iter_buf: ffi::mp_obj_iter_buf_t {
                base: ffi::mp_obj_base_t {
                    type_: ptr::null_mut(),
                },
                buf: [Obj::const_null(), Obj::const_null(), Obj::const_null()],
            },
        }
    }
}

pub struct Iter<'a> {
    iter: Obj,
    iter_buf: &'a mut IterBuf,
    finished: bool,
}

impl<'a> Iter<'a> {
    pub fn try_from_obj_with_buf(o: Obj, iter_buf: &'a mut IterBuf) -> Result<Self, Error> {
        // SAFETY:
        //  - In the common case, `ffi::mp_getiter` does not heap-allocate, but instead
        //    uses memory from the passed `iter_buf`. We maintain this invariant by
        //    taking a mut ref to `IterBuf` and tying it to the lifetime of returned
        //    `Iter`.
        //  - Raises if `o` is not iterable and in other cases as well.
        //  - Returned obj is referencing into `iter_buf`.
        // TODO: Use a fn that doesn't raise on non-iterable object.
        let iter = unsafe { ffi::mp_getiter(o, &mut iter_buf.iter_buf) };
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
        // SAFETY:
        //  - We assume that `mp_iternext` returns objects without any lifetime
        //    invariants, i.e. heap-allocated, unlike `mp_getiter`.
        //  - Can raise.
        let item = unsafe { ffi::mp_iternext(self.iter) };
        if item == Obj::const_stop_iteration() {
            self.finished = true;
            None
        } else {
            Some(item)
        }
    }
}

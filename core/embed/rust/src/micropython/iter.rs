use core::ptr;

use crate::{error::Error, micropython::obj::Obj};

use super::{ffi, runtime::catch_exception};

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
    caught_exception: Obj,
}

impl<'a> Iter<'a> {
    pub fn try_from_obj_with_buf(o: Obj, iter_buf: &'a mut IterBuf) -> Result<Self, Error> {
        // SAFETY:
        //  - In the common case, `ffi::mp_getiter` does not heap-allocate, but instead
        //    uses memory from the passed `iter_buf`. We maintain this invariant by
        //    taking a mut ref to `IterBuf` and tying it to the lifetime of returned
        //    `Iter`.
        //  - Returned obj is referencing into `iter_buf`.
        // EXCEPTION: Raises if `o` is not iterable and possibly in other cases too.
        let iter = catch_exception(|| unsafe { ffi::mp_getiter(o, &mut iter_buf.iter_buf) })?;
        Ok(Self {
            iter,
            iter_buf,
            finished: false,
            caught_exception: Obj::const_null(),
        })
    }

    pub fn error(&self) -> Option<Error> {
        if self.caught_exception.is_null() {
            None
        } else {
            Some(Error::CaughtException(self.caught_exception))
        }
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
        // EXCEPTION: Can raise from the underlying iterator.
        let item = catch_exception(|| unsafe { ffi::mp_iternext(self.iter) });
        match item {
            Err(Error::CaughtException(exc)) => {
                self.caught_exception = exc;
                None
            }
            Err(_) => panic!("unexpected error"),
            Ok(item) if item == Obj::const_stop_iteration() => {
                self.finished = true;
                None
            }
            Ok(item) => Some(item),
        }
    }
}

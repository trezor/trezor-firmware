use core::ptr;

use crate::{error::Error, micropython::obj::Obj};

use super::{ffi, runtime::catch_exception};

pub struct IterBuf {
    iter_buf: ffi::mp_obj_iter_buf_t,
    error_checking: bool,
    caught_exception: Obj,
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
            error_checking: false,
            caught_exception: Obj::const_null(),
        }
    }

    pub fn new_fallible() -> Self {
        let mut new = Self::new();
        new.error_checking = true;
        new
    }

    pub fn try_iterate(&mut self, o: Obj) -> Result<Iter, Error> {
        Iter::try_from_obj_with_buf(o, self)
    }

    pub fn error(&self) -> Option<Obj> {
        if !self.error_checking || self.caught_exception.is_null() {
            None
        } else {
            Some(self.caught_exception)
        }
    }
}

pub struct Iter<'a> {
    iter: Obj,
    // SAFETY:
    // In the typical case, `iter` is literally a pointer to `iter_buf`. We need to hold
    // an exclusive reference to `iter_buf` to avoid problems.
    iter_buf: &'a mut IterBuf,
    finished: bool,
}

impl<'a> Iter<'a> {
    fn try_from_obj_with_buf(o: Obj, iter_buf: &'a mut IterBuf) -> Result<Self, Error> {
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
        // EXCEPTION: Can raise from the underlying iterator.
        let item = catch_exception(|| unsafe { ffi::mp_iternext(self.iter) });
        match item {
            Err(Error::CaughtException(exc)) if self.iter_buf.error_checking => {
                self.iter_buf.caught_exception = exc;
                None
            }
            Err(_) => fatal_error!("Unexpected error"),
            Ok(item) if item == Obj::const_stop_iteration() => {
                self.finished = true;
                None
            }
            Ok(item) => Some(item),
        }
    }
}

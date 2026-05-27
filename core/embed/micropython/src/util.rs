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

use core::slice;

use crate::map::{Map, MapElem};
use crate::qstr::Attribute;
use crate::runtime::{catch_exception, raise_exception};
use crate::{Error, Obj, ffi};

/// Perform a call and convert errors into a raised MicroPython exception.
/// Should only called when returning from Rust to C. See `raise_exception` for
/// details.
pub unsafe fn try_or_raise<T>(func: impl FnOnce() -> Result<T, Error>) -> T {
    func().unwrap_or_else(|err| unsafe {
        raise_exception(err);
    })
}

/// Extract kwargs from a C call and pass them into Rust. Raise exception if an
/// error occurs. Should only called when returning from Rust to C. See
/// `raise_exception` for details.
#[allow(dead_code)]
pub unsafe fn try_with_kwargs(
    kwargs: *const Map,
    func: impl FnOnce(&Map) -> Result<Obj, Error>,
) -> Obj {
    let block = || {
        let kwargs = unsafe { kwargs.as_ref() }.ok_or(Error::MissingKwargs)?;

        func(kwargs)
    };
    unsafe { try_or_raise(block) }
}

/// Extract args and kwargs from a C call and pass them into Rust. Raise
/// exception if an error occurs. Should only called when returning from Rust to
/// C. See `raise_exception` for details.
pub unsafe fn try_with_args_and_kwargs(
    n_args: usize,
    args: *const Obj,
    kwargs: *const Map,
    func: impl FnOnce(&[Obj], &Map) -> Result<Obj, Error>,
) -> Obj {
    let block = || {
        let args = if args.is_null() {
            &[]
        } else {
            unsafe { slice::from_raw_parts(args, n_args) }
        };
        let kwargs = unsafe { kwargs.as_ref() }.ok_or(Error::MissingKwargs)?;

        func(args, kwargs)
    };
    unsafe { try_or_raise(block) }
}

/// Extract args and kwargs from a C call where args and kwargs are inlined, and
/// pass them into Rust. Raise exception if an error occurs. Should only called
/// when returning from Rust to C. See `raise_exception` for details.
pub unsafe fn try_with_args_and_kwargs_inline(
    n_args: usize,
    n_kw: usize,
    args: *const Obj,
    func: impl FnOnce(&[Obj], &Map) -> Result<Obj, Error>,
) -> Obj {
    let block = || {
        let args_slice: &[Obj];
        let kwargs_slice: &[MapElem];

        if args.is_null() {
            args_slice = &[];
            kwargs_slice = &[];
        } else {
            args_slice = unsafe { slice::from_raw_parts(args, n_args) };
            kwargs_slice = unsafe { slice::from_raw_parts(args.add(n_args).cast(), n_kw) };
        }

        let kw_map = Map::from_fixed(kwargs_slice);
        func(args_slice, &kw_map)
    };
    unsafe { try_or_raise(block) }
}

pub fn new_tuple(args: &[Obj]) -> Result<Obj, Error> {
    // SAFETY: Safe.
    // EXCEPTION: Raises if allocation fails, does not return NULL.
    catch_exception!(unsafe { ffi::mp_obj_new_tuple } => { args.len(), args.as_ptr() })
}

/// Create a new "attrtuple", which is essentially a namedtuple / ad-hoc object.
///
/// It is recommended to use the attr_tuple! macro instead of this function:
/// ```rust,ignore
/// let obj = attr_tuple! {
///     Qstr::MP_QSTR_language => header.language.try_into()?,
///     Qstr::MP_QSTR_version => util::new_tuple(&version_objs)?,
///     // ...
/// };
/// ```
pub fn new_attrtuple(fields: &'static [Attribute], values: &[Obj]) -> Result<Obj, Error> {
    if fields.len() != values.len() {
        return Err(Error::TypeError);
    }
    // SAFETY:
    // * `values` are copied into the tuple, but the `fields` array is stored as a
    //   pointer in the last tuple item. Hence the requirement that `fields` is
    //   'static. See objattrtuple.c:79
    // * we cast `field_qstrs` to the required type `ffi::qstr`, of which Attribute
    //   is a `#[repr(transparent)]` wrapper.
    // EXCEPTION: Raises if allocation fails, does not return NULL.
    catch_exception!(unsafe { ffi::mp_obj_new_attrtuple } =>
        {fields.as_ptr() as *const _, values.len(), values.as_ptr() })
}

pub fn modulo_format(format: Obj, args: &[Obj]) -> Result<Obj, Error> {
    catch_exception!(unsafe { ffi::str_modulo_format } =>
        { format, args.len(), args.as_ptr(), Obj::const_none() })
}

use core::slice;

use crate::{
    error::Error,
    micropython::{
        map::{Map, MapElem},
        obj::Obj,
        runtime::raise_exception,
    },
};

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

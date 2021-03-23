use core::slice;

use crate::{
    error::Error,
    micropython::{
        map::{Map, MapElem},
        obj::Obj,
        runtime::raise_value_error,
    },
};

pub fn try_or_raise<T>(func: impl FnOnce() -> Result<T, Error>) -> T {
    func().unwrap_or_else(|err| raise_value_error(err.as_cstr()))
}

pub fn try_with_kwargs(kwargs: *const Map, func: impl FnOnce(&Map) -> Result<Obj, Error>) -> Obj {
    try_or_raise(|| {
        let kwargs = unsafe { kwargs.as_ref() }.ok_or(Error::Missing)?;

        func(kwargs)
    })
}

pub fn try_with_args_and_kwargs(
    n_args: usize,
    args: *const Obj,
    kwargs: *const Map,
    func: impl FnOnce(&[Obj], &Map) -> Result<Obj, Error>,
) -> Obj {
    try_or_raise(|| {
        let args = if args.is_null() {
            &[]
        } else {
            unsafe { slice::from_raw_parts(args, n_args) }
        };
        let kwargs = unsafe { kwargs.as_ref() }.ok_or(Error::Missing)?;

        func(args, kwargs)
    })
}

pub fn try_with_args_and_kwargs_inline(
    n_args: usize,
    n_kw: usize,
    args: *const Obj,
    func: impl FnOnce(&[Obj], &Map) -> Result<Obj, Error>,
) -> Obj {
    try_or_raise(|| {
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
    })
}

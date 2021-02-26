use core::slice;

use crate::{
    error::Error,
    micropython::{map::Map, obj::Obj},
};

pub fn try_or_none(f: impl FnOnce() -> Result<Obj, Error>) -> Obj {
    f().unwrap_or(Obj::const_none())
}

pub fn try_with_kwargs(kw: *const Map, func: impl FnOnce(&Map) -> Result<Obj, Error>) -> Obj {
    unsafe { kw.as_ref() }
        .and_then(|kw| func(kw).ok())
        .unwrap_or(Obj::const_none())
}

pub fn try_with_args_and_kwargs(
    n_args: usize,
    args: *const Obj,
    kwargs: *const Map,
    func: impl FnOnce(&[Obj], &Map) -> Result<Obj, Error>,
) -> Obj {
    let args = if args.is_null() {
        &[]
    } else {
        unsafe { slice::from_raw_parts(args, n_args) }
    };
    unsafe { kwargs.as_ref() }
        .and_then(|kwargs| func(args, kwargs).ok())
        .unwrap_or(Obj::const_none())
}

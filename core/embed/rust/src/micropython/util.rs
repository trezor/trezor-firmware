use core::slice;

use heapless::Vec;

use super::{
    ffi,
    iter::IterBuf,
    map::{Map, MapElem},
    obj::Obj,
    qstr::Qstr,
    runtime::{catch_exception, raise_exception},
};
use crate::error::Error;

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
    let obj = catch_exception(|| unsafe { ffi::mp_obj_new_tuple(args.len(), args.as_ptr()) })?;
    Ok(obj)
}

/// Create a new "attrtuple", which is essentially a namedtuple / ad-hoc object.
///
/// It is recommended to use the attr_tuple! macro instead of this function:
/// ```
/// let obj = attr_tuple! {
///     Qstr::MP_QSTR_language => header.language.try_into()?,
///     Qstr::MP_QSTR_version => util::new_tuple(&version_objs)?,
///     // ...
/// }
/// ```
pub fn new_attrtuple(field_qstrs: &'static [Qstr], values: &[Obj]) -> Result<Obj, Error> {
    if field_qstrs.len() != values.len() {
        return Err(Error::TypeError);
    }
    // SAFETY:
    // * `values` are copied into the tuple, but the `fields` array is stored as a
    //   pointer in the last tuple item. Hence the requirement that `fields` is
    //   'static. See objattrtuple.c:79
    // * we cast `field_qstrs` to the required type `qstr`, which is internally
    //   usize. (py/qstr.h:48). This is valid for as long as Qstr is
    //   repr(transparent) and the only field is a usize. Check generated qstr.rs.
    // EXCEPTION: Raises if allocation fails, does not return NULL.
    let obj = catch_exception(|| unsafe {
        ffi::mp_obj_new_attrtuple(
            field_qstrs.as_ptr() as *const _,
            values.len(),
            values.as_ptr(),
        )
    })?;
    Ok(obj)
}

pub fn iter_into_array<T, E, const N: usize>(iterable: Obj) -> Result<[T; N], Error>
where
    T: TryFrom<Obj, Error = E>,
    Error: From<E>,
{
    let vec: Vec<T, N> = iter_into_vec(iterable)?;
    // Returns error if array.len() != N
    vec.into_array()
        .map_err(|_| value_error!("Invalid iterable length"))
}

pub fn iter_into_vec<T, E, const N: usize>(iterable: Obj) -> Result<Vec<T, N>, Error>
where
    T: TryFrom<Obj, Error = E>,
    Error: From<E>,
{
    let mut vec = Vec::<T, N>::new();
    for item in IterBuf::new().try_iterate(iterable)? {
        vec.push(item.try_into()?)
            .map_err(|_| value_error!("Invalid iterable length"))?;
    }
    Ok(vec)
}

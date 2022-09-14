use crate::{
    error::Error,
    micropython::{
        iter::{Iter, IterBuf},
        obj::Obj,
    },
};
use cstr_core::cstr;
use heapless::Vec;

pub fn iter_into_objs<const N: usize>(iterable: Obj) -> Result<[Obj; N], Error> {
    let err = Error::ValueError(cstr!("Invalid iterable length"));
    let mut vec = Vec::<Obj, N>::new();
    let mut iter_buf = IterBuf::new();
    for item in Iter::try_from_obj_with_buf(iterable, &mut iter_buf)? {
        vec.push(item).map_err(|_| err)?;
    }
    // Returns error if array.len() != N
    vec.into_array().map_err(|_| err)
}

pub fn iter_into_array<T, const N: usize>(iterable: Obj) -> Result<[T; N], Error>
where
    T: TryFrom<Obj, Error = Error>,
{
    let err = Error::ValueError(cstr!("Invalid iterable length"));
    let mut vec = Vec::<T, N>::new();
    let mut iter_buf = IterBuf::new();
    for item in Iter::try_from_obj_with_buf(iterable, &mut iter_buf)? {
        vec.push(item.try_into()?).map_err(|_| err)?;
    }
    // Returns error if array.len() != N
    vec.into_array().map_err(|_| err)
}

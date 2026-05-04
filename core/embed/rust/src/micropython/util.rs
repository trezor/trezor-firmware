use heapless::Vec;

use crate::strutil::hexlify;
use micropython::{
    buffer::{StrBuffer, get_buffer},
    error::Error,
    iter::IterBuf,
    obj::Obj,
};

pub fn iter_into_array<T, E, const N: usize>(iterable: Obj) -> Result<[T; N], Error>
where
    T: TryFrom<Obj, Error = E>,
    Error: From<E>,
{
    let vec: Vec<T, N> = iter_into_vec(iterable)?;
    // Returns error if array.len() != N
    vec.into_array()
        .map_err(|_| Error::ValueError(c"Invalid iterable length"))
}

pub fn iter_into_vec<T, E, const N: usize>(iterable: Obj) -> Result<Vec<T, N>, Error>
where
    T: TryFrom<Obj, Error = E>,
    Error: From<E>,
{
    let mut vec = Vec::<T, N>::new();
    for item in IterBuf::new().try_iterate(iterable)? {
        vec.push(item.try_into()?)
            .map_err(|_| Error::ValueError(c"Invalid iterable length"))?;
    }
    Ok(vec)
}

pub fn hexlify_bytes(obj: Obj, offset: usize, max_len: usize) -> Result<StrBuffer, Error> {
    if !obj.is_bytes() {
        return Err(Error::TypeError);
    }

    // Convert offset to byte representation, handle case where it points in the
    // middle of a byte.
    let bin_off = offset / 2;
    let hex_off = offset % 2;

    // SAFETY:
    // (a) only immutable references are taken
    // (b) reference is discarded before returning to micropython
    let bin_slice = unsafe { get_buffer(obj)? };
    let bin_slice = &bin_slice[bin_off..];

    let max_len = max_len & !1;
    let hex_len = (bin_slice.len() * 2).min(max_len);
    let result = StrBuffer::alloc_with(hex_len, move |buffer| hexlify(bin_slice, buffer))?;
    Ok(result.skip_prefix(hex_off))
}

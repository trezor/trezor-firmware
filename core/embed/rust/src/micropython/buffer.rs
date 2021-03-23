use core::{
    convert::TryFrom,
    ops::{Deref, DerefMut},
    ptr, slice,
};

use crate::{error::Error, micropython::obj::Obj};

use super::ffi;

/// Represents an immutable slice of bytes stored on the MicroPython heap and
/// owned by values that obey the `MP_BUFFER_READ` buffer protocol, such as
/// `bytes`, `str`, `bytearray` or `memoryview`.
///
/// # Safety
///
/// In most cases, it is unsound to store `Buffer` values in a GC-unreachable
/// location, such as static data. It is also unsound to let the contents be
/// modified while a reference to them is being held.
pub struct Buffer {
    ptr: *const u8,
    len: usize,
}

impl TryFrom<Obj> for Buffer {
    type Error = Error;

    fn try_from(obj: Obj) -> Result<Self, Self::Error> {
        let bufinfo = get_buffer_info(obj, ffi::MP_BUFFER_READ)?;

        Ok(Self {
            ptr: bufinfo.buf as _,
            len: bufinfo.len as _,
        })
    }
}

impl Deref for Buffer {
    type Target = [u8];

    fn deref(&self) -> &Self::Target {
        self.as_ref()
    }
}

impl AsRef<[u8]> for Buffer {
    fn as_ref(&self) -> &[u8] {
        buffer_as_ref(self.ptr, self.len)
    }
}

/// Represents a mutable slice of bytes stored on the MicroPython heap and
/// owned by values that obey the `MP_BUFFER_WRITE` buffer protocol, such as
/// `bytearray` or `memoryview`.
///
/// # Safety
///
/// In most cases, it is unsound to store `Buffer` values in a GC-unreachable
/// location, such as static data. It is also unsound to let the contents be
/// modified while the reference to them is being held.
pub struct BufferMut {
    ptr: *mut u8,
    len: usize,
}

impl TryFrom<Obj> for BufferMut {
    type Error = Error;

    fn try_from(obj: Obj) -> Result<Self, Self::Error> {
        let bufinfo = get_buffer_info(obj, ffi::MP_BUFFER_WRITE)?;

        Ok(Self {
            ptr: bufinfo.buf as _,
            len: bufinfo.len as _,
        })
    }
}

impl Deref for BufferMut {
    type Target = [u8];

    fn deref(&self) -> &Self::Target {
        self.as_ref()
    }
}

impl DerefMut for BufferMut {
    fn deref_mut(&mut self) -> &mut Self::Target {
        self.as_mut()
    }
}

impl AsRef<[u8]> for BufferMut {
    fn as_ref(&self) -> &[u8] {
        buffer_as_ref(self.ptr, self.len)
    }
}

impl AsMut<[u8]> for BufferMut {
    fn as_mut(&mut self) -> &mut [u8] {
        buffer_as_mut(self.ptr, self.len)
    }
}

fn get_buffer_info(obj: Obj, flags: u32) -> Result<ffi::mp_buffer_info_t, Error> {
    let mut bufinfo = ffi::mp_buffer_info_t {
        buf: ptr::null_mut(),
        len: 0,
        typecode: 0,
    };
    // SAFETY: We assume that if `ffi::mp_get_buffer` returns successfully,
    // `bufinfo.buf` contains a pointer to data of `bufinfo.len` bytes. Later
    // we consider this data either GC-allocated or effectively `'static`, embedding
    // them in `Buffer`/`BufferMut`.
    if unsafe { ffi::mp_get_buffer(obj, &mut bufinfo, flags as _) } {
        Ok(bufinfo)
    } else {
        Err(Error::NotBuffer)
    }
}

fn buffer_as_ref<'a>(ptr: *const u8, len: usize) -> &'a [u8] {
    if ptr.is_null() {
        // `ptr` can be null if len == 0.
        &[]
    } else {
        // SAFETY: We assume that `ptr` is pointing to memory:
        //  - without any mutable references,
        //  - valid and immutable in `'a`,
        //  - of at least `len` bytes.
        unsafe { slice::from_raw_parts(ptr, len) }
    }
}

fn buffer_as_mut<'a>(ptr: *mut u8, len: usize) -> &'a mut [u8] {
    if ptr.is_null() {
        // `ptr` can be null if len == 0.
        &mut []
    } else {
        // SAFETY: We assume that `ptr` is pointing to memory:
        //  - without any mutable references,
        //  - valid and mutable in `'a`,
        //  - of at least `len` bytes.
        unsafe { slice::from_raw_parts_mut(ptr, len) }
    }
}

use core::{convert::TryFrom, ops::Deref, ptr, slice};

use crate::{error::Error, micropython::obj::Obj};

use super::ffi;

pub struct Buffer {
    ptr: *mut u8,
    len: usize,
}

impl TryFrom<Obj> for Buffer {
    type Error = Error;

    fn try_from(obj: Obj) -> Result<Self, Self::Error> {
        let mut bufinfo = ffi::mp_buffer_info_t {
            buf: ptr::null_mut(),
            len: 0,
            typecode: 0,
        };
        if unsafe { ffi::mp_get_buffer(obj, &mut bufinfo, ffi::MP_BUFFER_READ as _) } {
            Ok(Self {
                ptr: bufinfo.buf as _,
                len: bufinfo.len as _,
            })
        } else {
            Err(Error::NotBuffer)
        }
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
        if self.ptr.is_null() {
            // `ptr` can be null if len == 0.
            &[]
        } else {
            // SAFETY: We assume that `ptr` is pointing to memory:
            //  - immutable for the whole lifetime of immutable ref of `self`.
            //  - of length `len` bytes.
            unsafe { slice::from_raw_parts(self.ptr, self.len) }
        }
    }
}

impl Buffer {
    pub unsafe fn as_mut(&mut self) -> &mut [u8] {
        if self.ptr.is_null() {
            // `ptr` can be null if len == 0.
            &mut []
        } else {
            // SAFETY: We assume that `ptr` is pointing to memory:
            //  - without any live references.
            //  - of length `len` bytes.
            unsafe { slice::from_raw_parts_mut(self.ptr, self.len) }
        }
    }
}

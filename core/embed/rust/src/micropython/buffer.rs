use core::{convert::TryFrom, ops::Deref, ptr, slice, str};

use crate::{error::Error, micropython::obj::Obj};

use super::ffi;

/// Represents an immutable UTF-8 string managed by MicroPython GC.
/// This either means static data, or a valid GC object.
///
/// # Safety
///
/// We assume that MicroPython is handling strings according to Python
/// semantics, i.e., that string data is immutable.
/// Furthermore, we assume that string data is always either static or a GC head
/// pointer, i.e., we can never obtain a pointer into the middle of a GC string.
///
/// Given the above assumptions about MicroPython strings, working with
/// StrBuffers in Rust is safe.
pub struct StrBuffer {
    ptr: *const u8,
    len: usize,
}

impl StrBuffer {
    pub fn empty() -> Self {
        Self::from("")
    }

    pub fn alloc(val: &str) -> Result<Self, Error> {
        // SAFETY:
        // We assume that if `gc_alloc` returns successfully, the result is a valid
        // pointer to GC-controlled memory of at least `val.len() + 1` bytes.
        unsafe {
            let raw = ffi::gc_alloc(val.len() + 1, 0) as *mut u8;
            if raw.is_null() {
                return Err(Error::AllocationFailed);
            }
            // SAFETY: Memory should be freshly allocated and as such cannot overlap.
            ptr::copy_nonoverlapping(val.as_ptr(), raw, val.len());
            // Null-terminate the string for C ASCIIZ compatibility. This will not be
            // reflected in Rust-visible slice, the zero byte is after the end.
            raw.add(val.len()).write(0);
            Ok(Self {
                ptr: raw,
                len: val.len(),
            })
        }
    }

    fn as_bytes(&self) -> &[u8] {
        if self.ptr.is_null() {
            &[]
        } else {
            unsafe { slice::from_raw_parts(self.ptr, self.len) }
        }
    }
}

impl Default for StrBuffer {
    fn default() -> Self {
        Self::empty()
    }
}

impl TryFrom<Obj> for StrBuffer {
    type Error = Error;

    fn try_from(obj: Obj) -> Result<Self, Self::Error> {
        if obj.is_qstr() || unsafe { ffi::mp_type_str.is_type_of(obj) } {
            let bufinfo = get_buffer_info(obj, ffi::MP_BUFFER_READ)?;
            let new = Self {
                ptr: bufinfo.buf as _,
                len: bufinfo.len as _,
            };

            // MicroPython _should_ ensure that values of type `str` are UTF-8.
            // Rust seems to be stricter in what it considers UTF-8 though.
            // If there is a mismatch, we return an error.
            let bytes = new.as_bytes();
            if str::from_utf8(bytes).is_err() {
                return Err(Error::TypeError);
            }

            Ok(new)
        } else {
            Err(Error::TypeError)
        }
    }
}

impl Deref for StrBuffer {
    type Target = str;

    fn deref(&self) -> &Self::Target {
        self.as_ref()
    }
}

impl AsRef<str> for StrBuffer {
    fn as_ref(&self) -> &str {
        // SAFETY:
        // - If constructed from a Rust `&str`, this is safe.
        // - If constructed from a MicroPython string, we check validity of UTF-8 at
        //   construction time. Python semantics promise not to mutate the underlying
        //   data from under us.
        unsafe { str::from_utf8_unchecked(self.as_bytes()) }
    }
}

impl From<&'static str> for StrBuffer {
    fn from(val: &'static str) -> Self {
        Self {
            ptr: val.as_ptr(),
            len: val.len(),
        }
    }
}

fn get_buffer_info(obj: Obj, flags: u32) -> Result<ffi::mp_buffer_info_t, Error> {
    let mut bufinfo = ffi::mp_buffer_info_t {
        buf: ptr::null_mut(),
        len: 0,
        typecode: 0,
    };
    // SAFETY: We assume that if `ffi::mp_get_buffer` returns successfully,
    // `bufinfo.buf` contains a pointer to data of `bufinfo.len` bytes.
    // EXCEPTION: Does not raise for Micropython's builtin types, and we don't
    // implement custom buffer protocols.
    if unsafe { ffi::mp_get_buffer(obj, &mut bufinfo, flags as _) } {
        Ok(bufinfo)
    } else {
        Err(Error::TypeError)
    }
}

/// Get an immutable reference to a buffer from a MicroPython object.
///
/// SAFETY:
/// The caller is responsible for ensuring immutability of the returned buffer,
/// in particular that:
/// (a) no mutable reference to the same buffer is held at the same time,
/// (b) the buffer is not modified in MicroPython while the reference to it is
/// being held.
pub unsafe fn get_buffer<'a>(obj: Obj) -> Result<&'a [u8], Error> {
    let bufinfo = get_buffer_info(obj, ffi::MP_BUFFER_READ)?;

    if bufinfo.buf.is_null() {
        // `bufinfo.buf` can be null if len == 0.
        Ok(&[])
    } else {
        // SAFETY: We assume that `bufinfo.buf` is pointing to memory:
        //  - valid in `'a`
        //  - of at least `bufinfo.len` bytes
        // The caller is responsible for ensuring that:
        //  - there are no mutable references
        //  - that the buffer is immutable in `'a`
        Ok(unsafe { slice::from_raw_parts(bufinfo.buf as _, bufinfo.len) })
    }
}

/// Get a mutable reference to a buffer from a MicroPython object.
///
/// SAFETY:
/// The caller is responsible for ensuring uniqueness of the mutable reference,
/// in particular that:
/// (a) no other reference to the same buffer is held at the same time,
/// (b) the buffer is not modified in MicroPython while the reference to it is
/// being held.
pub unsafe fn get_buffer_mut<'a>(obj: Obj) -> Result<&'a mut [u8], Error> {
    let bufinfo = get_buffer_info(obj, ffi::MP_BUFFER_WRITE)?;

    if bufinfo.buf.is_null() {
        // `bufinfo.buf` can be null if len == 0.
        Ok(&mut [])
    } else {
        // SAFETY: We assume that `bufinfo.buf` is pointing to memory:
        //  - valid and mutable in `'a`,
        //  - of at least `bufinfo.len` bytes.
        // The caller is responsible for ensuring that:
        //  - there are no other references
        //  - the buffer is not mutated outside of Rust's control.
        Ok(unsafe { slice::from_raw_parts_mut(bufinfo.buf as _, bufinfo.len) })
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for StrBuffer {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        self.as_ref().trace(t)
    }
}

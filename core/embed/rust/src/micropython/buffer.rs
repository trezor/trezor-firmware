use core::{convert::TryFrom, ops::Deref, ptr, slice, str};

use crate::{error::Error, micropython::obj::Obj, strutil::hexlify};

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
///
/// The `off` field represents offset from the `ptr` and allows us to do
/// substring slices while keeping the head pointer as required by GC.
#[repr(C)]
#[derive(Copy, Clone)]
pub struct StrBuffer {
    ptr: *const u8,
    len: u16,
    off: u16,
}

impl StrBuffer {
    pub fn empty() -> Self {
        Self::from("")
    }

    // SAFETY:
    // Caller is responsible for ensuring that data under `ptr` is valid for the
    // whole lifetime of the result, plus possible copies/clones/offsets.
    // This generally holds for GC-managed pointers and for static data.
    // Dangerous with anything else.
    pub unsafe fn from_ptr_and_len(ptr: *const u8, len: usize) -> Self {
        Self {
            ptr,
            len: unwrap!(len.try_into()),
            off: 0,
        }
    }

    pub fn alloc(val: &str) -> Result<Self, Error> {
        unsafe {
            Self::alloc_with(val.len(), |buffer| {
                // SAFETY: Memory should be freshly allocated and as such cannot overlap.
                ptr::copy_nonoverlapping(val.as_ptr(), buffer.as_mut_ptr(), buffer.len())
            })
        }
    }

    pub fn alloc_with(len: usize, func: impl FnOnce(&mut [u8])) -> Result<Self, Error> {
        // SAFETY:
        // We assume that if `gc_alloc` returns successfully, the result is a valid
        // pointer to GC-controlled memory of at least `val.len() + 1` bytes.
        unsafe {
            let raw = ffi::gc_alloc(len + 1, 0) as *mut u8;
            if raw.is_null() {
                return Err(Error::AllocationFailed);
            }

            // SAFETY: GC returns valid pointers, slice is discarded after `func`.
            let bytes = slice::from_raw_parts_mut(raw, len);
            // GC returns uninitialized memory which we must make sure to overwrite,
            // otherwise leftover references may keep alive otherwise dead
            // objects. Zero the entire buffer so we don't have to rely on
            // `func` doing it.
            bytes.fill(0);
            func(bytes);
            str::from_utf8(bytes).map_err(|_| Error::OutOfRange)?;

            // Null-terminate the string for C ASCIIZ compatibility. This will not be
            // reflected in Rust-visible slice, the zero byte is after the end.
            raw.add(len).write(0);
            // SAFETY: pointer is GC-managed.
            Ok(Self::from_ptr_and_len(raw, len))
        }
    }

    fn as_bytes(&self) -> &[u8] {
        if self.ptr.is_null() {
            &[]
        } else {
            unsafe { slice::from_raw_parts(self.ptr.add(self.off.into()), self.len.into()) }
        }
    }

    pub fn skip_prefix(&self, skip_bytes: usize) -> Self {
        let off: u16 = unwrap!(skip_bytes.try_into());
        assert!(off <= self.len);
        assert!(self.as_ref().is_char_boundary(skip_bytes));
        Self {
            ptr: self.ptr,
            // Does not overflow because `off <= self.len`.
            len: self.len - off,
            // `self.off + off` could only overflow if `self.off + self.len` could overflow, and
            // given that `off` only advances by as much as `len` decreases, that should not be
            // possible either.
            off: self.off + off,
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
        if obj.is_str() {
            let bufinfo = get_buffer_info(obj, ffi::MP_BUFFER_READ)?;
            // SAFETY: bufinfo.buf should point to a GC head pointer or static data.
            let new = unsafe { Self::from_ptr_and_len(bufinfo.buf as _, bufinfo.len) };

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
        // - If constructed by `offset()`, we expect the input to be UTF-8 and check
        //   that we split the string at character boundary.
        unsafe { str::from_utf8_unchecked(self.as_bytes()) }
    }
}

impl From<&'static str> for StrBuffer {
    fn from(val: &'static str) -> Self {
        // SAFETY: Safe for &'static strs.
        // Do not try to do it with arbitrary &'a str.
        unsafe { Self::from_ptr_and_len(val.as_ptr(), val.len()) }
    }
}

#[cfg(feature = "debug")]
impl ufmt::uDebug for StrBuffer {
    fn fmt<W>(&self, f: &mut ufmt::Formatter<'_, W>) -> Result<(), W::Error>
    where
        W: ufmt::uWrite + ?Sized,
    {
        f.write_str("StrBuffer(")?;
        f.write_str(self.as_ref())?;
        f.write_str(")")?;
        Ok(())
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
/// The returned value is NOT guaranteed to be a head pointer, so the
/// destination might get GC'd. Do not store the reference.
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
/// The returned value is NOT guaranteed to be a head pointer, so the
/// destination might get GC'd. Do not store the reference.
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

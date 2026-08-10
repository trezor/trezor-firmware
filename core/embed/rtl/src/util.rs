/// Explicit fat pointer representation
///
/// Should be always used when passing slices into C.
///
/// Coerces the internal pointer to NULL in case length is zero, to make pointer
/// validation safer and easier in C. Typically, C will allow either (a) NULL
/// pointer or (b) pointer to valid memory. But Rust zero-length slices are
/// pointers whose int value is `align_of<T>`, which is decidedly _not_ valid
/// memory. This way, C side will be satisfied.
///
/// # Safety
///
/// A FatPtr is a fat representation of a Rust pointer type. It intentionally
/// does not have an associated lifetime. When created from a slice that later
/// goes out of scope, it may become invalid. Treat with care.
#[repr(C)]
pub struct FatPtr<T> {
    ptr: *const T,
    len: usize,
}

impl<T> FatPtr<T> {
    /// Create a null fatpointer with zero length
    pub fn null() -> Self {
        Self {
            ptr: core::ptr::null(),
            len: 0,
        }
    }

    /// Create a fat pointer from a ptr + len
    pub fn from_ptr_and_len(ptr: *const T, len: usize) -> Self {
        if ptr.is_null() {
            Self::null()
        } else {
            Self { ptr, len }
        }
    }

    /// View the fat pointer as a slice
    ///
    /// Returns `None` if the fat pointer is null, a possibly empty slice otherwise.
    ///
    /// The returned slice borrows from `self`, so its lifetime is capped by the
    /// scope of the `FatPtr` value. This is appropriate for a certain style of
    /// C FFI calls, where you create a `FatPtr` from an incoming ptr+len, then
    /// pass the result of `as_slice()` into Rust code for processing. In such
    /// case the lifetime guarantees that the slice will stop existing when we
    /// return back to C.
    ///
    /// # Safety
    ///
    /// If the pointer is non-null and length is non-zero, the call reduces to
    /// [`core::slice::from_raw_parts`], so all its safety properties apply; in
    /// short, the pointer must point to valid aligned memory of length `len`.
    pub unsafe fn as_slice(&self) -> Option<&[T]> {
        if self.ptr.is_null() {
            None
        } else if self.len == 0 {
            Some(&[])
        } else {
            Some(unsafe { core::slice::from_raw_parts(self.ptr, self.len) })
        }
    }

    pub fn is_null(&self) -> bool {
        self.ptr.is_null()
    }

    pub fn ptr(&self) -> *const T {
        self.ptr
    }

    pub fn len(&self) -> usize {
        self.len
    }

    pub fn is_empty(&self) -> bool {
        self.len == 0
    }
}

impl<T> From<&[T]> for FatPtr<T> {
    fn from(s: &[T]) -> Self {
        if s.is_empty() {
            Self::null()
        } else {
            Self {
                ptr: s.as_ptr(),
                len: s.len(),
            }
        }
    }
}

// Helper for converting &str to (signed) char*
impl From<&str> for FatPtr<cty::c_char> {
    fn from(s: &str) -> Self {
        let charptr = FatPtr::from(s.as_bytes());
        Self {
            ptr: charptr.ptr() as *const cty::c_char,
            len: charptr.len(),
        }
    }
}

/// Constructs a string from a C string.
///
/// # Safety
///
/// The caller is responsible that the pointer is valid, which means that:
/// (a) it points to a memory containing a valid C string (zero-terminated
/// sequence of characters), and
/// (b) that the pointer has appropriate lifetime.
pub unsafe fn from_c_str<'a>(c_str: *const cty::c_char) -> Option<&'a str> {
    if c_str.is_null() {
        return None;
    }
    unsafe {
        let bytes = core::ffi::CStr::from_ptr(c_str as _).to_bytes();
        if bytes.is_ascii() {
            Some(core::str::from_utf8_unchecked(bytes))
        } else {
            None
        }
    }
}

/// Construct str from a C array.
///
/// # Safety
///
/// The caller is responsible that the pointer is valid, which means that:
/// (a) it points to a memory containing array of characters, with length `len`,
/// and
/// (b) that the pointer has appropriate lifetime.
pub unsafe fn from_c_array<'a>(c_str: *const cty::c_char, len: usize) -> Option<&'a str> {
    if c_str.is_null() {
        return None;
    }
    unsafe {
        let slice = core::slice::from_raw_parts(c_str as *const u8, len);
        if slice.is_ascii() {
            Some(core::str::from_utf8_unchecked(slice))
        } else {
            None
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_fat_ptr() {
        let s = "Hello, world!";
        let fp = FatPtr::from(s);
        assert_eq!(fp.ptr() as usize, s.as_ptr() as usize);
        assert_eq!(fp.len(), s.len());
    }

    #[test]
    fn test_nullptr() {
        let fp = FatPtr::<i32>::null();
        assert!(fp.is_null());
        assert_eq!(fp.ptr(), core::ptr::null());
        assert_eq!(fp.len(), 0);
        assert!(fp.is_empty());
    }

    #[test]
    fn test_empty_slice() {
        let s: &[u64] = &[];
        let fp = FatPtr::from(s);
        assert!(fp.is_null());
        assert_eq!(fp.ptr(), core::ptr::null());
        assert_eq!(fp.len(), 0);
        assert!(fp.is_empty());
    }
}

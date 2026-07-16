/// Explicit fat pointer representation
///
/// Useful when passing slices into C
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

    /// Convert the fat pointer into a slice
    ///
    /// Returns `None` if the fat pointer is null, a slice otherwise.
    ///
    /// # Safety
    ///
    /// The call reduces to [`core::slice::from_raw_parts`], so all its safety
    /// properties apply.
    pub unsafe fn into_slice<'a>(self) -> Option<&'a [T]> {
        if self.ptr.is_null() {
            None
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
        Self {
            ptr: s.as_ptr(),
            len: s.len(),
        }
    }
}

// Helper for converting &str to (signed) char*
impl From<&str> for FatPtr<cty::c_char> {
    fn from(s: &str) -> Self {
        Self {
            ptr: s.as_ptr() as *const cty::c_char,
            len: s.len(),
        }
    }
}

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

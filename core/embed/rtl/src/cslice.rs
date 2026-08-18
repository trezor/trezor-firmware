use core::marker::PhantomData;

/// Explicit manual representation of a slice.
///
/// Should be always used when converting between Rust slices and C ptr+len
/// pairs.
///
/// A CSlice is a pointer + length pair, its behavior tuned to expectations of C
/// code.
///
/// The internal pointer **can be NULL**, which C tends to conflate with the
/// "empty slice" concept. C function will typically evaluate the pointer first,
/// and only look at the length if the pointer is non-NULL. If we naively
/// converted a Rust empty slice into a pointer, we would get a non-NULL
/// dangling pointer (typically with an int value of `align_of<T>`, pointing to
/// invalid memory).
///
/// Rust-side accessors always return an `Option<&[T]>` to cover the NULL case.
///
/// For this reason, CSlice coerces both zero-length slices (from Rust side) and
/// NULL-pointer pairs (from C side) into the same [`CSlice::null()`] object.
///
/// # Safety
///
/// `CSlice` carries a lifetime parameter `'a`, which is required for soundness
/// on Rust side.
///
/// Note, however, that `'a` does not figure in any return types. Views into the
/// slice are either bounded by lifetime of `&self`, or (unsafely) unbounded.
///
/// There are two kinds of CSlices:
///
/// ## Created from a Rust slice
///
/// When a `CSlice` is safely constructed via `From<&'a [T]>`, the lifetime
/// bound ensures that the CSlice does not outlive the original slice. Viewing
/// via `as_slice()` / `as_ascii_str()` is safe because the view also cannot
/// outlive the original.
///
/// ## Created from a C pointer
///
/// When unsafely constructed via `CSlice::from_ptr_and_len()`, the lifetime
/// `'a` is unbounded. The caller must ensure that the `CSlice` object does not
/// outlive pointer validity; typically, you will construct a `CSlice` in an
/// `extern "C"` function and only keep it alive in its scope.
///
/// Given this assumption, viewing via `as_slice()` / `as_ascii_str()` is
/// again safe because they don't outlive the owner object.
pub struct CSlice<'a, T> {
    ptr: *const T,
    len: usize,
    _marker: PhantomData<&'a T>,
}

impl<'a, T> CSlice<'a, T> {
    /// Create a null CSlice with zero length
    pub const fn null() -> Self {
        Self {
            ptr: core::ptr::null(),
            len: 0,
            _marker: PhantomData,
        }
    }

    /// Create a CSlice from a ptr + len
    ///
    /// # Safety
    ///
    /// If `ptr` is NULL, or `len` is 0, the result is a null CSlice. Using a
    /// null CSlice is safe.
    ///
    /// If the `ptr` is non-null and `len` is non-zero, then `ptr` must:
    /// * be correctly aligned for type `T`
    /// * point to a valid slice of `len` elements of type `T`
    /// * be valid for the lifetime of the CSlice object (but not necessarily
    ///   for `'a`).
    ///
    /// The constructed CSlice object has an unbounded lifetime parameter `'a`,
    /// but this never figures in any function return signatures, so it doesn't
    /// actually affect safety.
    pub const unsafe fn from_ptr_and_len(ptr: *const T, len: usize) -> Self {
        if ptr.is_null() || len == 0 {
            Self::null()
        } else {
            Self {
                ptr,
                len,
                _marker: PhantomData,
            }
        }
    }

    /// Construct a slice with an unbounded lifetime from the ptr and len.
    ///
    /// # Safety
    ///
    /// Discards the owner's lifetime bound. Internal helper for both:
    /// * `as_slice()`, which immediately binds the lifetime to &self, and
    /// * `into_unbounded_slice()`, which consumes and discards self.
    const unsafe fn make_unbounded_slice<'b>(&self) -> Option<&'b [T]> {
        if self.ptr.is_null() {
            None
        } else if self.len == 0 {
            Some(&[])
        } else {
            Some(unsafe { core::slice::from_raw_parts(self.ptr, self.len) })
        }
    }

    /// Convert the CSlice into a slice with an unbounded lifetime.
    ///
    /// This is the escape hatch for CSlices created from C pointers whose
    /// lifetime is longer than "scope of called function" (e.g., pointers to
    /// static memory).
    ///
    /// # Safety
    ///
    /// By calling this, CSlice gives up any claim of lifetime management. It's
    /// up to the caller to handle the lifetime of the returned slice manually
    /// -- preferably by bounding it with an appropriate context.
    pub const unsafe fn into_unbounded_slice<'b>(self) -> Option<&'b [T]> {
        // SAFETY: responsibility of the caller
        unsafe { self.make_unbounded_slice() }
    }

    /// View the CSlice as a slice
    ///
    /// Returns `None` if the CSlice is null, a possibly empty slice otherwise.
    ///
    /// The returned slice borrows from `self`, so its lifetime is capped by the
    /// scope of the `CSlice` value. This is appropriate for a certain style of
    /// C FFI calls, where you create a `CSlice` from an incoming ptr+len, then
    /// pass the result of `as_slice()` into Rust code for processing. In such
    /// case the lifetime guarantees that the slice will stop existing when we
    /// return back to C.
    pub fn as_slice(&self) -> Option<&[T]> {
        // SAFETY: lifetime of returned slice is bounded by &self
        unsafe { self.make_unbounded_slice() }
    }

    /// Check if the CSlice is null
    pub const fn is_null(&self) -> bool {
        self.ptr.is_null()
    }

    /// Get the raw pointer part
    pub const fn ptr(&self) -> *const T {
        self.ptr
    }

    /// Get the length of the slice
    pub const fn len(&self) -> usize {
        self.len
    }

    /// Check if the slice is empty
    pub const fn is_empty(&self) -> bool {
        self.len == 0
    }
}

macro_rules! impl_as_ascii_str {
    ($ty:ty) => {
        impl CSlice<'_, $ty> {
            /// View a CSlice as an ASCII string
            ///
            /// Returns a `&str` representation if the pointer is non-null and
            /// ASCII, `None` otherwise. Notably: if the string is valid but
            /// non-ASCII, you also get `None`.
            pub fn as_ascii_str(&self) -> Option<&str> {
                // SAFETY: lifetime of returned slice is bounded by &self
                unsafe { str_from_c_array(self.ptr as *const _, self.len) }
            }

            /// Convert the CSlice into an ASCII string with an unbounded lifetime.
            ///
            /// Escape hatch for CSlice created from C pointers whose lifetime
            /// is longer than "scope of called function" (e.g., pointers to
            /// static memory).
            ///
            /// # Safety
            ///
            /// By calling this, CSlice gives up any claim of lifetime
            /// management. In this it is equivalent to
            /// [`CSlice::into_unbounded_slice()`], see its safety notes for
            /// details.
            pub unsafe fn into_unbounded_ascii_str<'b>(self) -> Option<&'b str> {
                // SAFETY: responsibility of the caller
                unsafe { str_from_c_array(self.ptr as *const _, self.len) }
            }
        }
    };
}

impl_as_ascii_str!(i8);
impl_as_ascii_str!(u8);

impl CSlice<'_, u8> {
    /// Create a CSlice from a null-terminated C string
    ///
    /// Calculates the length of the string up to the first null byte
    /// and converts it to a CSlice.
    ///
    /// # Safety
    ///
    /// The caller is responsible for ensuring that the underlying pointer
    /// points to a valid null-terminated C string.
    pub unsafe fn from_c_str(c_str: *const cty::c_char) -> Self {
        if c_str.is_null() {
            return Self::null();
        }
        // we use CStr to calculate length and make a slice for us
        // SAFETY: caller should provide a valid C string
        let cstr = unsafe { core::ffi::CStr::from_ptr(c_str as _) };
        cstr.to_bytes().into()
    }
}

impl<'a, T> From<&'a [T]> for CSlice<'a, T> {
    fn from(s: &'a [T]) -> Self {
        if s.is_empty() {
            Self::null()
        } else {
            Self {
                ptr: s.as_ptr(),
                len: s.len(),
                _marker: PhantomData,
            }
        }
    }
}

impl<'a, T> From<Option<&'a [T]>> for CSlice<'a, T> {
    fn from(s: Option<&'a [T]>) -> Self {
        s.map(From::from).unwrap_or_else(Self::null)
    }
}

// Helper for converting &str to (signed) char*
impl<'a> From<&'a str> for CSlice<'a, cty::c_char> {
    fn from(s: &str) -> Self {
        let charptr = CSlice::from(s.as_bytes());
        Self {
            ptr: charptr.ptr() as *const cty::c_char,
            len: charptr.len(),
            _marker: PhantomData,
        }
    }
}

impl<'a> From<Option<&'a str>> for CSlice<'a, cty::c_char> {
    fn from(s: Option<&'a str>) -> Self {
        s.map(From::from).unwrap_or_else(Self::null)
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
///
/// The returned lifetime is unbounded and the caller is responsible for
/// bounding it.
unsafe fn str_from_c_array<'a>(c_str: *const cty::c_char, len: usize) -> Option<&'a str> {
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
        let fp = CSlice::from(s);
        assert_eq!(fp.ptr() as usize, s.as_ptr() as usize);
        assert_eq!(fp.len(), s.len());
    }

    #[test]
    fn test_nullptr() {
        let fp = CSlice::<i32>::null();
        assert!(fp.is_null());
        assert_eq!(fp.ptr(), core::ptr::null());
        assert_eq!(fp.len(), 0);
        assert!(fp.is_empty());
    }

    #[test]
    fn test_empty_slice() {
        let s: &[u64] = &[];
        let fp = CSlice::from(s);
        assert!(fp.is_null());
        assert_eq!(fp.ptr(), core::ptr::null());
        assert_eq!(fp.len(), 0);
        assert!(fp.is_empty());
    }

    #[test]
    fn test_from_option() {
        let s: Option<&[u64]> = None;
        let fp = CSlice::from(s);
        assert!(fp.is_null());

        let array = [1u64, 2u64, 3u64];
        let s = Some(&array[..]);
        let fp = CSlice::from(s);
        assert!(!fp.is_null());
        assert_eq!(fp.ptr(), array.as_ptr());
        assert_eq!(fp.len(), array.len());

        let s: Option<&str> = None;
        let fp = CSlice::from(s);
        assert!(fp.is_null());

        let text = "Hello, world!";
        let s = Some(text);
        let fp = CSlice::from(s);
        assert!(!fp.is_null());
        assert_eq!(fp.ptr(), text.as_bytes().as_ptr() as *const _);
        assert_eq!(fp.len(), text.len());
    }
}

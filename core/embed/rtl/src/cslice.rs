//! Explicit manual representation of a slice.
//!
//! Should always be used when converting between Rust slices and C ptr+len
//! pairs.
//!
//! A CSlice is a pointer + length pair, its behavior tuned to expectations of
//! C code.
//!
//! ## NULL/empty coercion
//!
//! In typical C code, _either_ a NULL pointer _or_ zero length tends to
//! indicate an empty slice. C functions will often evaluate the pointer first,
//! and only look at the length if the pointer is non-NULL.
//!
//! In contrast, Rust represents empty slices with a dangling non-NULL pointer
//! (typically with an int value of `align_of<T>`) and zero length. When passed
//! to C, the pointer part is non-NULL but invalid.
//!
//! For this reason, both [`CSlice`] and [`CSliceMut`] coerce zero-length
//! slices (from Rust side) and NULL-pointer pairs (from C side) into the same
//! null representation.
//!
//! Valid CSlice objects are always either:
//!
//! * a NULL pointer and zero length (called a "null CSlice"), or
//! * a pointer to valid memory of non-zero length.
//!
//! The shared ptr+len storage and this NULL/empty coercion live in
//! [`CSlicePtr`], which both types wrap privately, using `PhantomData` to
//! attach a correct lifetime and ownership.

use core::marker::PhantomData;

/// Shared implementation of `CSlice` / `CSliceMut` logic.
///
/// The `CSlicePtr` type is analogous to a pointer: constructing and moving it
/// around is always safe. It also has the unsafe capability to dereference into
/// a slice. The safety of such operation is delegated to the caller.
///
/// A "null" `CSlicePtr` is an object where `ptr` is NULL and `len` is zero. It
/// is not possible to construct either a null `ptr` with non-zero length, or a
/// non-null `ptr` with zero length.
#[derive(Debug, Copy, Clone, PartialEq, Eq)]
struct CSlicePtr<T> {
    ptr: *const T,
    len: usize,
}

impl<T> CSlicePtr<T> {
    /// Create a null `CSlicePtr` with zero length.
    const fn null() -> Self {
        Self {
            ptr: core::ptr::null(),
            len: 0,
        }
    }

    /// Create a `CSlicePtr` from a ptr + len.
    ///
    /// If `ptr` is NULL, or `len` is 0, the result is a null `CSlicePtr`.
    const fn from_ptr_and_len(ptr: *const T, len: usize) -> Self {
        if ptr.is_null() || len == 0 {
            Self::null()
        } else {
            Self { ptr, len }
        }
    }

    /// Create a `CSlicePtr` from a Rust slice.
    ///
    /// If the slice is empty, the result is a null `CSlicePtr`.
    const fn from_slice(slice: &[T]) -> Self {
        if slice.is_empty() {
            Self::null()
        } else {
            Self {
                ptr: slice.as_ptr(),
                len: slice.len(),
            }
        }
    }

    /// Create a `CSlicePtr` from a Rust mutable slice.
    ///
    /// If we went through `from_slice` for the mutable case, we'd lose
    /// provenance information and get a "read-only" pointer. _Likely_ to work
    /// in practice, but UB per spec and may end up miscompiled.
    ///
    /// FFS. And yes, MIRI confirms this.
    ///
    /// If the slice is empty, the result is a null `CSlicePtr`.
    const fn from_slice_mut(slice: &mut [T]) -> Self {
        if slice.is_empty() {
            Self::null()
        } else {
            Self {
                ptr: slice.as_mut_ptr(),
                len: slice.len(),
            }
        }
    }

    /// Dereference to a slice with an unbounded lifetime.
    ///
    /// # Safety
    ///
    /// If the `CSlicePtr` is null, the result is an empty slice. This is always
    /// safe.
    ///
    /// If the `CSlicePtr` is non-null, constructs a slice via
    /// [`core::slice::from_raw_parts`].
    ///
    /// Caller is responsible for:
    ///
    /// 1. Making sure that `from_raw_parts` requirements are met: `ptr` is
    ///    aligned, valid for reads of the appropriate array length, there are
    ///    no live mutable references to the same memory, and the memory is not
    ///    mutated during the lifetime of the returned slice.
    /// 2. Properly bounding the lifetime of the returned slice.
    const unsafe fn make_unbounded_slice<'b>(&self) -> &'b [T] {
        if self.is_empty() {
            &[]
        } else {
            // SAFETY: caller responsibility
            unsafe { core::slice::from_raw_parts(self.ptr, self.len) }
        }
    }

    /// Dereference to a mutable slice with an unbounded lifetime.
    ///
    /// Mutable counterpart to [`Self::make_unbounded_slice`]. Returns an empty
    /// slice if the `CSlicePtr` is null.
    ///
    /// # Safety
    ///
    /// If the `CSlicePtr` is null, the result is an empty slice. This is always
    /// safe.
    ///
    /// If the `CSlicePtr` is non-null and non-zero, constructs a mutable slice
    /// via [`core::slice::from_raw_parts_mut`]. Caller is responsible for:
    ///
    /// 1. Making sure that the internal pointer has the correct provenance
    ///    (that is, if from a Rust slice, it's `from_slice_mut()` rather than
    ///    `from_slice()`)
    /// 2. Making sure that `from_raw_parts_mut` requirements are met: `ptr` is
    ///    aligned, valid for reads and writes of the appropriate array length,
    ///    there are no other live references to the same memory, and the memory
    ///    is not accessed except through the returned slice, for the duration
    ///    of the slice's lifetime.
    /// 3. Properly bounding the lifetime of the returned slice.
    const unsafe fn make_unbounded_slice_mut<'b>(&self) -> &'b mut [T] {
        if self.is_empty() {
            &mut []
        } else {
            // SAFETY: caller responsibility
            unsafe { core::slice::from_raw_parts_mut(self.ptr as *mut T, self.len) }
        }
    }

    /// Get the raw pointer part.
    pub const fn ptr(&self) -> *const T {
        self.ptr
    }

    /// Get the length of the slice.
    pub const fn len(&self) -> usize {
        self.len
    }

    /// Check if the slice is empty.
    ///
    /// True for null `CSlicePtr`s, false otherwise.
    pub const fn is_empty(&self) -> bool {
        debug_assert!((self.len == 0) == self.ptr.is_null());
        self.ptr.is_null()
    }

    /// Cast the `CSlicePtr` to a different type.
    ///
    /// # Safety
    ///
    /// While the cast itself is safe (unsafety happens at dereference time),
    /// caller should be careful when using `cast()` that the resulting
    /// `CSlicePtr` will be valid for the destination type.
    pub const fn cast<U>(self) -> CSlicePtr<U> {
        CSlicePtr {
            ptr: self.ptr.cast(),
            len: self.len,
        }
    }
}

/// Explicit manual representation of a shared slice.
///
/// Should be always used when converting between Rust slices and C ptr+len
/// pairs. See the [module-level documentation](self) for the NULL/empty-slice
/// semantics shared with [`CSliceMut`].
///
/// Deliberately not `Copy` / `Clone`. This would muddy the semantics: CSlice
/// may be a wrapper around a C pointer whose lifetime is unknown, so the
/// lifetime of derived Rust slices should be conservative.
///
/// In particular, [`Self::into_unbounded_slice()`] takes `self` by value so
/// that explicitly erasing the lifetime visibly consumes the `CSlice`. With
/// `Copy`, a caller could keep using the original and the "value has been
/// consumed" signal would be lost.
pub struct CSlice<'a, T> {
    inner: CSlicePtr<T>,
    _marker: PhantomData<&'a T>,
}

impl<T> CSlice<'_, T> {
    /// Create a null CSlice with zero length.
    pub const fn null() -> Self {
        Self {
            inner: CSlicePtr::null(),
            _marker: PhantomData,
        }
    }

    /// Create a `CSlice` from a `*const T` and length.
    ///
    /// Typically used at the FFI boundary when a Rust function is called from
    /// C.
    ///
    /// # Safety
    ///
    /// If `ptr` is NULL, or `len` is 0, the result is a null CSlice. Using a
    /// null CSlice is safe.
    ///
    /// If the `ptr` is non-null and `len` is non-zero, then `ptr` must:
    ///
    /// * be correctly aligned for type `T`,
    /// * point to a valid slice of `len` elements of type `T`,
    /// * be valid for reads for the lifetime of the constructed `CSlice`,
    /// * the pointed-to memory not be mutated for the lifetime of the
    ///   constructed `CSlice`.
    ///
    /// The lifetime parameter `'a` of the returned `CSlice` is unbounded. The
    /// caller should typically discard the `CSlice` when the enclosing function
    /// returns, or otherwise correctly bound `'a` to whatever is appropriate
    /// for the originating pointer.
    pub const unsafe fn from_ptr_and_len(ptr: *const T, len: usize) -> Self {
        Self {
            inner: CSlicePtr::from_ptr_and_len(ptr, len),
            _marker: PhantomData,
        }
    }

    /// View the `CSlice` as a slice.
    pub const fn as_slice(&self) -> &[T] {
        // SAFETY: lifetime of returned slice is bounded by &self
        unsafe { self.inner.make_unbounded_slice() }
    }

    /// Convert the CSlice into a slice with an unbounded lifetime.
    ///
    /// This is the escape hatch for CSlices created from C pointers whose
    /// lifetime is longer than "scope of called function" (e.g., pointers to
    /// static memory).
    ///
    /// # Safety
    ///
    /// By calling this, CSlice gives up any claim of lifetime management.
    /// It's up to the caller to handle the lifetime of the returned slice
    /// manually -- preferably by bounding it with an appropriate context.
    pub const unsafe fn into_unbounded_slice<'b>(self) -> &'b [T] {
        // SAFETY: responsibility of the caller
        unsafe { self.inner.make_unbounded_slice() }
    }

    /// Get the raw pointer part.
    pub const fn ptr(&self) -> *const T {
        self.inner.ptr()
    }

    /// Get the length of the slice.
    pub const fn len(&self) -> usize {
        self.inner.len()
    }

    /// Check if the slice is empty.
    pub const fn is_empty(&self) -> bool {
        self.inner.is_empty()
    }
}

macro_rules! impl_as_ascii_str {
    ($ty:ty) => {
        impl<'a> CSlice<'a, $ty> {
            /// Convert the `CSlice` to an ASCII string with an unbounded lifetime.
            ///
            /// Returns a `&str` representation if the slice represents a
            /// (possibly empty) ASCII string, `None` otherwise.
            ///
            /// (The reason for ASCII is so that the calling code can avoid
            /// pulling `str::from_utf8` into the binary; `<[u8]>::is_ascii()`
            /// is significantly smaller in code size.)
            ///
            /// # Safety
            ///
            /// The returned lifetime is unbounded, and the caller is responsible
            /// for bounding it.
            const unsafe fn make_unbounded_ascii_str<'b>(&self) -> Option<&'b str> {
                if self.is_empty() {
                    return Some("");
                }
                // SAFETY: caller responsibility
                let u8_slice = unsafe { self.inner.cast::<u8>().make_unbounded_slice() };
                if u8_slice.is_ascii() {
                    // SAFETY: ASCII is a subset of UTF-8
                    Some(unsafe { core::str::from_utf8_unchecked(u8_slice) })
                } else {
                    None
                }
            }

            /// View a CSlice as an ASCII string.
            ///
            /// Returns a `&str` representation if the slice represents a (possibly
            /// empty) ASCII string, `None` otherwise.
            pub const fn as_ascii_str(&self) -> Option<&str> {
                // SAFETY: lifetime of returned slice is bounded by &self
                unsafe { self.make_unbounded_ascii_str() }
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
            pub const unsafe fn into_unbounded_ascii_str<'b>(self) -> Option<&'b str> {
                // SAFETY: responsibility of the caller
                unsafe { self.make_unbounded_ascii_str() }
            }
        }
    };
}

impl_as_ascii_str!(i8);
impl_as_ascii_str!(u8);

impl CSlice<'_, u8> {
    /// Create a CSlice from a null-terminated C string.
    ///
    /// Calculates the length of the string up to the first null byte
    /// and converts it to a CSlice.
    ///
    /// # Safety
    ///
    /// If the `c_str` is NULL, the result is a null CSlice. Using a null CSlice
    /// is safe.
    ///
    /// If the `c_str` is non-null, the caller is responsible for ensuring that
    /// the underlying pointer points to a valid null-terminated C string that
    /// is valid for reads and not mutated during the lifetime of the
    /// constructed `CSlice`.
    ///
    /// The lifetime parameter `'a` of the returned `CSlice` is unbounded. The
    /// caller should typically discard the `CSlice` when the enclosing function
    /// returns, or otherwise correctly bound `'a` to whatever is appropriate
    /// for the originating pointer.
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
        Self {
            inner: CSlicePtr::from_slice(s),
            _marker: PhantomData,
        }
    }
}

impl<'a, T> From<Option<&'a [T]>> for CSlice<'a, T> {
    fn from(s: Option<&'a [T]>) -> Self {
        s.map(From::from).unwrap_or_else(Self::null)
    }
}

// Helper for converting &str to (possibly signed) char*
impl<'a> From<&'a str> for CSlice<'a, cty::c_char> {
    fn from(s: &str) -> Self {
        Self {
            inner: CSlicePtr::from_slice(s.as_bytes()).cast(),
            _marker: PhantomData,
        }
    }
}

impl<'a> From<Option<&'a str>> for CSlice<'a, cty::c_char> {
    fn from(s: Option<&'a str>) -> Self {
        s.map(From::from).unwrap_or_else(Self::null)
    }
}

/// Explicit manual representation of a mutable slice.
///
/// Mutable counterpart of [`CSlice`]. Should be always used when converting
/// between Rust mutable slices and C ptr+len pairs that are written through.
///
/// See the [module-level documentation](self) for the NULL/empty-slice
/// semantics shared with [`CSlice`].
pub struct CSliceMut<'a, T> {
    inner: CSlicePtr<T>,
    _marker: PhantomData<&'a mut T>,
}

impl<T> CSliceMut<'_, T> {
    /// Create a null CSliceMut with zero length.
    pub const fn null() -> Self {
        Self {
            inner: CSlicePtr::null(),
            _marker: PhantomData,
        }
    }

    /// Create a `CSliceMut` from a `*mut T` and length.
    ///
    /// Typically used at the FFI boundary when a Rust function is called from
    /// C.
    ///
    /// # Safety
    ///
    /// If `ptr` is NULL, or `len` is 0, the result is a null `CSliceMut`. Using
    /// a null `CSliceMut` is safe.
    ///
    /// If the `ptr` is non-null and `len` is non-zero, then `ptr` must:
    ///
    /// * be correctly aligned for type `T`,
    /// * point to a valid slice of `len` elements of type `T`,
    /// * be valid for reads and writes during the lifetime of the constructed
    ///   `CSliceMut`,
    /// * be exclusive: no other Rust reference (shared or exclusive) to the
    ///   same memory may be alive while the `CSliceMut` exists,
    /// * the pointed-to memory must not be accessed except through the returned
    ///   `CSliceMut` instance during its lifetime.
    ///
    /// The lifetime parameter `'a` of the returned `CSliceMut` is
    /// unbounded. The caller should typically discard the `CSliceMut` when the
    /// enclosing function returns, or otherwise correctly bound `'a` to
    /// whatever is appropriate for the originating pointer.
    pub const unsafe fn from_ptr_and_len(ptr: *mut T, len: usize) -> Self {
        Self {
            inner: CSlicePtr::from_ptr_and_len(ptr, len),
            _marker: PhantomData,
        }
    }

    /// Convert the `CSliceMut` into a mutable slice with an unbounded lifetime.
    ///
    /// This is the escape hatch for `CSliceMut`s created from C pointers whose
    /// lifetime is longer than "scope of called function" (e.g., pointers to
    /// static memory).
    ///
    /// # Safety
    ///
    /// By calling this, `CSliceMut` gives up any claim of lifetime management.
    /// It's up to the caller to handle the lifetime of the returned slice
    /// manually -- preferably by bounding it with an appropriate context.
    pub const unsafe fn into_unbounded_slice_mut<'b>(self) -> &'b mut [T] {
        // SAFETY: responsibility of the caller
        unsafe { self.inner.make_unbounded_slice_mut() }
    }

    /// View the `CSliceMut` as a mutable slice.
    pub const fn as_slice_mut(&mut self) -> &mut [T] {
        // SAFETY: lifetime of returned slice is bounded by &mut self; exclusivity
        // of the underlying pointer is a constructor invariant.
        unsafe { self.inner.make_unbounded_slice_mut() }
    }

    /// View the `CSliceMut` as a slice.
    pub const fn as_slice(&self) -> &[T] {
        // SAFETY: lifetime of returned slice is bounded by &self; exclusivity
        // of the underlying pointer is a constructor invariant, and a shared
        // borrow is always valid where an exclusive one is.
        unsafe { self.inner.make_unbounded_slice() }
    }

    /// Get the raw pointer part.
    pub const fn ptr(&self) -> *mut T {
        self.inner.ptr() as *mut T
    }

    /// Get the length of the slice.
    pub const fn len(&self) -> usize {
        self.inner.len()
    }

    /// Check if the slice is empty.
    pub const fn is_empty(&self) -> bool {
        self.inner.is_empty()
    }
}

impl<'a, T> From<&'a mut [T]> for CSliceMut<'a, T> {
    fn from(s: &'a mut [T]) -> Self {
        Self {
            inner: CSlicePtr::from_slice_mut(s),
            _marker: PhantomData,
        }
    }
}

impl<'a, T> From<Option<&'a mut [T]>> for CSliceMut<'a, T> {
    fn from(s: Option<&'a mut [T]>) -> Self {
        s.map(From::from).unwrap_or_else(Self::null)
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
        assert_eq!(fp.as_ascii_str(), Some(s));
    }

    #[test]
    fn test_nullptr() {
        let fp = CSlice::<i32>::null();
        assert_eq!(fp.ptr(), core::ptr::null());
        assert_eq!(fp.len(), 0);
        assert!(fp.is_empty());
        assert_eq!(fp.as_slice(), &[]);
    }

    #[test]
    fn test_empty_slice() {
        let s: &[u64] = &[];
        let fp = CSlice::from(s);
        assert_eq!(fp.ptr(), core::ptr::null());
        assert_eq!(fp.len(), 0);
        assert!(fp.is_empty());
        assert_eq!(fp.as_slice(), &[]);
    }

    #[test]
    fn test_from_option() {
        let s: Option<&[u64]> = None;
        let fp = CSlice::from(s);
        assert!(fp.is_empty());
        assert_eq!(fp.as_slice(), &[]);

        let array = [1u64, 2u64, 3u64];
        let s = Some(&array[..]);
        let fp = CSlice::from(s);
        assert!(!fp.is_empty());
        assert_eq!(fp.ptr(), array.as_ptr());
        assert_eq!(fp.len(), array.len());
        assert_eq!(fp.as_slice(), &array);

        let s: Option<&str> = None;
        let fp = CSlice::from(s);
        assert!(fp.is_empty());
        assert_eq!(fp.as_ascii_str(), Some(""));

        let text = "Hello, world!";
        let s = Some(text);
        let fp = CSlice::from(s);
        assert!(!fp.is_empty());
        assert_eq!(fp.ptr(), text.as_bytes().as_ptr() as *const _);
        assert_eq!(fp.len(), text.len());
        assert_eq!(fp.as_ascii_str(), Some(text));
    }

    #[test]
    fn test_from_mut_slice() {
        let mut array = [1u64, 2u64, 3u64];
        let expected_ptr = array.as_mut_ptr();
        let mut fp = CSliceMut::from(&mut array[..]);
        assert!(!fp.is_empty());
        assert_eq!(fp.ptr(), expected_ptr);
        assert_eq!(fp.len(), 3);
        fp.as_slice_mut()[0] = 9;
        assert_eq!(fp.as_slice(), &[9, 2, 3]);
        assert_eq!(array[0], 9);

        let mut empty: [u64; 0] = [];
        let mut fp = CSliceMut::from(&mut empty[..]);
        assert!(fp.is_empty());
        assert_eq!(fp.len(), 0);
        assert_eq!(fp.as_slice(), &[]);
        assert_eq!(fp.as_slice_mut(), &mut []);

        let s: Option<&mut [u64]> = None;
        let mut fp = CSliceMut::from(s);
        assert!(fp.is_empty());
        assert_eq!(fp.as_slice_mut(), &mut []);
    }

    #[test]
    fn test_from_ptr_and_len_coercion() {
        let array = [1u32, 2, 3];

        // non-null + zero length → null
        let fp = unsafe { CSlice::from_ptr_and_len(array.as_ptr(), 0) };
        assert!(fp.is_empty());
        assert_eq!(fp.ptr(), core::ptr::null());
        assert_eq!(fp.as_slice(), &[]);

        // null + non-zero length → null
        let fp = unsafe { CSlice::<u32>::from_ptr_and_len(core::ptr::null(), 4) };
        assert!(fp.is_empty());
        assert_eq!(fp.as_slice(), &[]);

        // valid ptr+len
        let fp = unsafe { CSlice::from_ptr_and_len(array.as_ptr(), array.len()) };
        assert_eq!(fp.as_slice(), &array);

        let mut array = [1u32, 2, 3];
        let mut fp = unsafe { CSliceMut::from_ptr_and_len(array.as_mut_ptr(), 0) };
        assert!(fp.is_empty());
        assert_eq!(fp.as_slice_mut(), &mut []);

        let mut fp = unsafe { CSliceMut::from_ptr_and_len(array.as_mut_ptr(), array.len()) };
        fp.as_slice_mut()[1] = 7;
        assert_eq!(array, [1, 7, 3]);
    }

    #[test]
    fn test_as_ascii_str() {
        assert_eq!(CSlice::<u8>::null().as_ascii_str(), Some(""));
        assert_eq!(CSlice::from("").as_ascii_str(), Some(""));
        assert_eq!(CSlice::from("abc").as_ascii_str(), Some("abc"));

        let non_ascii: &[u8] = &[0x80, 0xFF];
        assert_eq!(CSlice::from(non_ascii).as_ascii_str(), None);

        // i8 path (unix-style c_char)
        let i8_bytes: &[i8] = &[b'o' as i8, b'k' as i8];
        assert_eq!(CSlice::from(i8_bytes).as_ascii_str(), Some("ok"));
        assert_eq!(CSlice::<i8>::null().as_ascii_str(), Some(""));

        let i8_non_ascii: &[i8] = &[-1];
        assert_eq!(CSlice::from(i8_non_ascii).as_ascii_str(), None);
    }

    #[test]
    fn test_from_c_str() {
        let fp = unsafe { CSlice::from_c_str(core::ptr::null()) };
        assert!(fp.is_empty());
        assert_eq!(fp.as_ascii_str(), Some(""));

        let empty = c"";
        let fp = unsafe { CSlice::from_c_str(empty.as_ptr().cast()) };
        assert!(fp.is_empty());
        assert_eq!(fp.as_ascii_str(), Some(""));

        let hello = c"hello";
        let fp = unsafe { CSlice::from_c_str(hello.as_ptr().cast()) };
        assert_eq!(fp.as_slice(), b"hello");
        assert_eq!(fp.as_ascii_str(), Some("hello"));
    }

    #[test]
    fn test_from_str_empty() {
        let fp: CSlice<'_, cty::c_char> = CSlice::from("");
        assert!(fp.is_empty());
        assert_eq!(fp.ptr(), core::ptr::null());
    }

    #[test]
    fn test_into_unbounded() {
        static DATA: [u8; 3] = *b"xyz";
        let fp = unsafe { CSlice::from_ptr_and_len(DATA.as_ptr(), DATA.len()) };
        let slice: &'static [u8] = unsafe { fp.into_unbounded_slice() };
        assert_eq!(slice, b"xyz");

        let fp = unsafe { CSlice::from_ptr_and_len(DATA.as_ptr(), DATA.len()) };
        let s: Option<&'static str> = unsafe { fp.into_unbounded_ascii_str() };
        assert_eq!(s, Some("xyz"));

        let empty = unsafe { CSlice::<u8>::null().into_unbounded_ascii_str() };
        assert_eq!(empty, Some(""));
    }
}

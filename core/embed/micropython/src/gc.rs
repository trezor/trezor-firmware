use core::{
    alloc::Layout,
    ops::{Deref, DerefMut},
    ptr::{self, NonNull},
};

use crate::error::Error;

use super::ffi;

/// A pointer type for values on the garbage-collected heap.
pub struct Gc<T: ?Sized>(NonNull<T>);

impl<T: ?Sized> Clone for Gc<T> {
    fn clone(&self) -> Self {
        *self
    }
}

impl<T: ?Sized> Copy for Gc<T> {}

impl<T> Gc<T> {
    /// Allocate memory on the heap managed by the MicroPython garbage collector
    /// and then place `v` into it.
    ///
    /// `flags` can be an int value built out of constants in the ffi module.
    /// The current MicroPython only supports GC_ALLOC_FLAG_HAS_FINALISER, which
    /// will cause the __del__ method to be called when the object is
    /// garbage collected.
    ///
    /// SAFETY:
    /// Flag GC_ALLOC_FLAG_HAS_FINALISER can only be used with Python objects
    /// that have a base as their first element
    unsafe fn alloc(v: T, flags: u32) -> Result<Self, Error> {
        let layout = Layout::for_value(&v);
        debug_assert!(
            layout.size() > 0,
            "Zero-sized allocations are not supported"
        );
        // TODO: Assert that `layout.align()` is the same as the GC alignment.
        // SAFETY:
        //  - Unfortunately we cannot respect `layout.align()` as MicroPython GC does
        //    not support custom alignment.
        //  - `ptr` is guaranteed to stay valid as long as it's reachable from the stack
        //    or the MicroPython heap.
        // EXCEPTION: Returns null instead of raising.
        unsafe {
            let raw = ffi::gc_alloc(layout.size(), flags);
            if raw.is_null() {
                return Err(Error::AllocationFailed);
            }
            let typed = raw.cast();
            ptr::write(typed, v);
            Ok(Self::from_raw(typed))
        }
    }

    /// Allocate memory on the heap managed by the MicroPython garbage collector
    /// and then place `v` into it. `v` will _not_ get its destructor called.
    pub fn new(v: T) -> Result<Self, Error> {
        unsafe {
            // SAFETY: No flag is used
            Self::alloc(v, 0)
        }
    }

    /// Allocate memory on the heap managed by the MicroPython garbage
    /// collector, place `v` into it, and register for finalisation.
    ///
    /// `v` will **not** get its destructor called automatically! However, if
    /// `v` is a Python-style object (has a base as its first field), and
    /// has a `__del__` method, it will be called when the object is garbage
    /// collected. You can use this to implement custom finalisation, in
    /// which you can, e.g., invoke the Drop implementation.
    /// SAFETY:
    /// Can only be used with Python objects that have a base as their
    /// first element
    pub unsafe fn new_with_custom_finaliser(v: T) -> Result<Self, Error> {
        unsafe { Self::alloc(v, ffi::GC_ALLOC_FLAG_HAS_FINALISER as _) }
    }
}

impl<T: Default> Gc<[T]> {
    /// Allocate slice on the heap managed by the MicroPython garbage collector
    /// and fill with default values.
    pub fn new_slice(len: usize) -> Result<Self, Error> {
        let layout = Layout::array::<T>(len).unwrap();
        // TODO: Assert that `layout.align()` is the same as the GC alignment.
        // SAFETY:
        //  - Unfortunately we cannot respect `layout.align()` as MicroPython GC does
        //    not support custom alignment.
        //  - `ptr` is guaranteed to stay valid as long as it's reachable from the stack
        //    or the MicroPython heap.
        // EXCEPTION: Returns null instead of raising.
        unsafe {
            let raw = ffi::gc_alloc(layout.size(), 0);
            if raw.is_null() {
                return Err(Error::AllocationFailed);
            }
            let typed: *mut T = raw.cast();
            for i in 0..len {
                ptr::write(typed.add(i), T::default());
            }
            let array_ptr = ptr::slice_from_raw_parts_mut(typed, len);
            Ok(Self::from_raw(array_ptr as _))
        }
    }
}

impl<T: ?Sized> Gc<T> {
    /// Construct a `Gc` from a raw pointer.
    ///
    /// # Safety
    ///
    /// This function is unsafe because the caller has to guarantee that `ptr`
    /// is pointing to a memory understood by the MicroPython GC, that is:
    /// - previously allocated through `Gc::new()` or `gc_alloc()`, or
    /// - through the MicroPython interpreter, or
    /// - one of the GC roots (sys.argv, sys.modules, etc.).
    pub unsafe fn from_raw(ptr: *mut T) -> Self {
        // SAFETY: The caller must guarantee that `ptr` is something the MicroPython GC
        // can reason about.
        unsafe { Self(NonNull::new_unchecked(ptr)) }
    }

    /// Convert `this` into a raw pointer. This will _not_ drop the contained
    /// value.
    pub fn into_raw(this: Self) -> *mut T {
        this.0.as_ptr()
    }

    /// Return a mutable reference to the value.
    ///
    /// # Safety
    ///
    /// `Gc` values can originate in the MicroPython interpreter, and these can
    /// be both shared and mutable. Before calling this function, you have to
    /// ensure that `this` is unique for the whole lifetime of the
    /// returned mutable reference.
    pub unsafe fn as_mut(this: &mut Self) -> &mut T {
        // SAFETY: The caller must guarantee that `this` meets all the requirements for
        // a mutable reference.
        unsafe { this.0.as_mut() }
    }

    /// Return a immutable reference to the value.
    ///
    /// # Safety
    ///
    /// `Gc` values can originate in the MicroPython interpreter, and these can
    /// be both shared and mutable. Before calling this function, you have to
    /// ensure that `this` does not get externally mutated and nobody
    /// holds a mutable reference.
    pub unsafe fn as_ref(this: &Self) -> &T {
        // SAFETY: The caller must guarantee that `this` meets all the requirements for
        // a immutable reference.
        unsafe { this.0.as_ref() }
    }
}

impl<T: ?Sized> Deref for Gc<T> {
    type Target = T;

    fn deref(&self) -> &Self::Target {
        unsafe { self.0.as_ref() }
    }
}

/// Box-like allocation on the GC heap.
///
/// Values allocated using GcBox are guaranteed to be only owned by that
/// particular GcBox instance. This makes them safe to mutate, and they run
/// destructors when dropped.
///
/// Suitable for use in cases where you would normally use Rust's native Box
/// type -- i.e., typically for storing sub-values in a struct, possibly also
/// for returning values from functions.
///
/// While general unsizing is not available, you can use the `coerce!` macro to
/// safely cast the box to a trait object.
///
/// # Safety and usage notes
///
/// One caveat of using GcBox is that it still always needs to be visible to the
/// GC -- that is, stored in a struct which is allocated on the GC heap, on the
/// call stack, or reachable from one of the GC roots.
///
/// Specifically, it is generally unsafe to store a GcBox in a global variable.
///
/// When a GcBox is stored in a struct, which itself is allocated via raw GC,
/// the containing struct might get GC'd, which will cause GcBox not to get
/// dropped, which in turn will prevent GcBox's contents from getting dropped.
pub struct GcBox<T: ?Sized>(Gc<T>);

impl<T> GcBox<T> {
    /// Allocate memory on the heap managed by the MicroPython GC and then place
    /// `value` into it.
    ///
    /// `value` _will_ get its Drop implementation called when the GcBox is
    /// dropped.
    pub fn new(value: T) -> Result<Self, Error> {
        Ok(Self(Gc::new(value)?))
    }
}

impl<T: ?Sized> GcBox<T> {
    /// Leak contents of the box as a pointer.
    ///
    /// # Safety
    ///
    /// The value will not be dropped. If necessary, the caller is responsible
    /// for dropping it manually, e.g., via `ptr::drop_in_place`.
    pub fn into_raw(this: Self) -> *mut T {
        let result = Gc::into_raw(this.0);
        core::mem::forget(this);
        result
    }

    /// Construct a `GcBox` from a raw pointer.
    ///
    /// # Safety
    ///
    /// This is only safe for pointers _allocated on the MicroPython GC heap_
    /// via `gc_alloc()`. Specifically, unlike `Gc::from_raw`, it is unsafe
    /// to construct a GcBox from ROM values, even those that are trackable
    /// by the GC.
    ///
    /// This is because the Drop implementation of GcBox calls `gc_free()` on
    /// the pointer.
    ///
    /// In addition, the caller must ensure that it is safe to apply box-like
    /// semantics to the value, namely that:
    ///  * nobody else has the pointer to the value, so that it is safe to
    ///    create mutable references to it
    ///  * the value is going to be dropped when the GcBox is dropped.
    pub unsafe fn from_raw(ptr: *mut T) -> Self {
        // SAFETY: just a wrapper around Gc::from_raw
        Self(unsafe { Gc::from_raw(ptr) })
    }

    /// Leak contents of the box as a regular Gc allocation.
    ///
    /// This gives up the unique ownership. It is no longer possible to safely
    /// mutably borrow the value, and its destructor will not be called when
    /// it is dropped. In exchange, it is possible to return Gc instance to
    /// MicroPython.
    pub fn leak(self) -> Gc<T> {
        let inner = self.0;
        core::mem::forget(self);
        inner
    }
}

/// Type-cast GcBox contents to a `dyn Trait` object.
macro_rules! coerce {
    ($t:path, $v:expr) => {
        // SAFETY: we are just re-wrapping the pointer, so all safety requirements
        // of `GcBox::from_raw` are upheld.
        // Rust type system will not allow us to cast to a trait object that is not
        // implemented by the type.
        unsafe { GcBox::from_raw(GcBox::into_raw($v) as *mut dyn $t) }
    };
}

pub(crate) use coerce;

impl<T: ?Sized> Deref for GcBox<T> {
    type Target = T;

    fn deref(&self) -> &Self::Target {
        self.0.deref()
    }
}

impl<T: ?Sized> DerefMut for GcBox<T> {
    fn deref_mut(&mut self) -> &mut Self::Target {
        // SAFETY: We are the sole owner of the allocated value, and we are borrowed
        // mutably.
        unsafe { Gc::as_mut(&mut self.0) }
    }
}

impl<T: ?Sized> Drop for GcBox<T> {
    fn drop(&mut self) {
        let ptr = Gc::into_raw(self.0);
        // SAFETY: We are the sole owner of the allocated value, and we are being
        // dropped.
        unsafe {
            ptr::drop_in_place(ptr);
            ffi::gc_free(ptr.cast());
        }
    }
}

#[cfg(test)]
mod test {
    use core::cell::Cell;

    use crate::micropython::testutil::mpy_init;

    use super::*;

    struct SignalDrop<'a>(&'a Cell<bool>);

    impl Drop for SignalDrop<'_> {
        fn drop(&mut self) {
            self.0.set(true);
        }
    }

    trait Foo {
        fn foo(&self) -> i32;
    }

    impl Foo for SignalDrop<'_> {
        fn foo(&self) -> i32 {
            42
        }
    }

    #[test]
    fn gc_nodrop() {
        unsafe { mpy_init() };

        let drop_signalled = Cell::new(false);
        {
            let _gc = Gc::new(SignalDrop(&drop_signalled)).unwrap();
        }
        assert!(!drop_signalled.get());
    }

    #[test]
    fn gcbox_drop() {
        unsafe { mpy_init() };

        let drop_signalled = Cell::new(false);
        {
            let _gcbox = GcBox::new(SignalDrop(&drop_signalled)).unwrap();
        }
        assert!(drop_signalled.get());
    }

    #[test]
    fn gc_raw_roundtrip() {
        unsafe { mpy_init() };

        let gc = Gc::new(42).unwrap();
        let ptr = Gc::into_raw(gc);
        let wrapped = unsafe { Gc::from_raw(ptr) };
        let retrieved = Gc::into_raw(wrapped);
        assert_eq!(ptr, retrieved);
    }

    #[test]
    fn gcbox_raw_roundtrip() {
        unsafe { mpy_init() };

        let drop_signalled = Cell::new(false);

        {
            let gcbox = GcBox::new(SignalDrop(&drop_signalled)).unwrap();
            assert!(!drop_signalled.get());
            let ptr = GcBox::into_raw(gcbox);
            assert!(!drop_signalled.get());
            let wrapped = unsafe { GcBox::from_raw(ptr) };
            assert!(!drop_signalled.get());
            let retrieved = GcBox::into_raw(wrapped);
            assert!(!drop_signalled.get());
            assert_eq!(ptr, retrieved);

            let _rewrapped = unsafe { GcBox::from_raw(ptr) };
        }
        assert!(drop_signalled.get());
    }

    #[test]
    fn test_coerce() {
        unsafe { mpy_init() };

        let drop_signalled = Cell::new(false);
        {
            let gcbox = GcBox::new(SignalDrop(&drop_signalled)).unwrap();
            let coerced: GcBox<dyn Foo> = coerce!(Foo, gcbox);
            assert!(!drop_signalled.get());
            assert_eq!(coerced.foo(), 42);
        }
        assert!(drop_signalled.get());
    }
}

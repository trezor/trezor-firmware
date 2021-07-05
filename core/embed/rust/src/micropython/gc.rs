use core::{
    alloc::Layout,
    ops::Deref,
    ptr::{self, NonNull},
};

use super::ffi;

/// A pointer type for values on the garbage-collected heap.
///
/// Although a garbage-collected pointer type technically should implement
/// `Copy` and `Clone`, we avoid doing this until proven necessary.
pub struct Gc<T: ?Sized>(NonNull<T>);

impl<T> Gc<T> {
    /// Allocate memory on the heap managed by the MicroPython garbage collector
    /// and then place `v` into it. `v` will _not_ get its destructor called.
    pub fn new(v: T) -> Self {
        let layout = Layout::for_value(&v);
        // TODO: Assert that `layout.align()` is the same as the GC alignment.
        // SAFETY:
        //  - Unfortunately we cannot respect `layout.align()` as MicroPython GC does
        //    not support custom alignment.
        //  - `ptr` is guaranteed to stay valid as long as it's reachable from the stack
        //    or the MicroPython heap.
        unsafe {
            let raw = ffi::gc_alloc(layout.size(), 0).cast();
            ptr::write(raw, v);
            Self::from_raw(raw)
        }
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
}

impl<T: ?Sized> Deref for Gc<T> {
    type Target = T;

    fn deref(&self) -> &Self::Target {
        unsafe { self.0.as_ref() }
    }
}

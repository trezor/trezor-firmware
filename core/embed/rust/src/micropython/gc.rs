use core::{
    alloc::Layout,
    marker::Unsize,
    ops::{CoerceUnsized, Deref, DispatchFromDyn},
    ptr::{self, NonNull},
};

use super::ffi;

pub struct Gc<T: ?Sized>(NonNull<T>);

impl<T: ?Sized + Unsize<U>, U: ?Sized> CoerceUnsized<Gc<U>> for Gc<T> {}
impl<T: ?Sized + Unsize<U>, U: ?Sized> DispatchFromDyn<Gc<U>> for Gc<T> {}

impl<T> Gc<T> {
    pub fn new(v: T) -> Self {
        let layout = Layout::for_value(&v);
        // TODO: Assert that `layout.align()` is the same as the GC alignment.
        // SAFETY:
        //  - Unfortunately we cannot respect `layout.align()` as Micropython GC does
        //    not support custom alignment.
        //  - `ptr` is guaranteed to stay valid as long as it's reachable from the stack
        //    or the Micropython heap.
        unsafe {
            let raw = ffi::gc_alloc(layout.size(), 0).cast();
            ptr::write(raw, v);
            Self::from_raw(raw)
        }
    }

    pub unsafe fn as_mut(&mut self) -> &mut T {
        // SAFETY: Caller needs to uphold the usual aliasing guarantees.
        unsafe { self.0.as_mut() }
    }
}

impl<T: ?Sized> Gc<T> {
    pub unsafe fn from_raw(ptr: *mut T) -> Self {
        // SAFETY: `ptr` has to point to a previously GC-allocated memory.
        unsafe { Self(NonNull::new_unchecked(ptr)) }
    }

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

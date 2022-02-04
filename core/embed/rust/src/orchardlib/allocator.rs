/// Implementation of the global allocator. Enables usage of `core::alloc` crate.
use crate::micropython::ffi;
use core::alloc::{GlobalAlloc, Layout};

// TODO: Lift this module to higher level.

pub struct Alloc;

unsafe impl GlobalAlloc for Alloc {
    unsafe fn alloc(&self, layout: Layout) -> *mut u8 {
        unsafe {
            let raw = ffi::gc_alloc(layout.size(), 0);
            if raw.is_null() {
                panic!("Allocation failed!");
            }
            raw.cast()
        }
    }

    // Deallocation solved by micropython garbage collector.
    unsafe fn dealloc(&self, _ptr: *mut u8, _layout: Layout) {}
}

#[global_allocator]
static A: Alloc = Alloc;
